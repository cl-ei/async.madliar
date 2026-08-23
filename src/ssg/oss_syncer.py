import os
import logging
import hashlib
import traceback
from pathlib import Path
from typing import Dict, Set, Tuple

import oss2


class OSSSyncer:
    """将本地目录增量同步到 OSS，支持 HTML 去后缀 + Content-Type 自动推断。"""

    # 文本类资源必须带 charset，否则 CDN 回源后浏览器可能乱码
    MIME_MAP = {
        '.html': 'text/html; charset=utf-8',
        '.htm':  'text/html; charset=utf-8',
        '.css':  'text/css; charset=utf-8',
        '.js':   'application/javascript; charset=utf-8',
        '.mjs':  'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.xml':  'application/xml; charset=utf-8',
        '.txt':  'text/plain; charset=utf-8',
        '.svg':  'image/svg+xml',
        '.png':  'image/png',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif':  'image/gif',
        '.webp': 'image/webp',
        '.avif': 'image/avif',
        '.ico':  'image/x-icon',
        '.woff': 'font/woff',
        '.woff2':'font/woff2',
        '.ttf':  'font/ttf',
        '.otf':  'font/otf',
        '.wasm': 'application/wasm',
        '.mp4':  'video/mp4',
        '.webm': 'video/webm',
        '.pdf':  'application/pdf',
    }

    def __init__(self, access_key_id: str, access_key_secret: str,
                 endpoint: str, bucket_name: str):
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #
    def sync_to_remote(self, local: str, remote: str) -> bool:
        """
        将本地目录增量同步到 OSS（含删除远端多余文件）。

        Args:
            local:  本地目录路径，如 "/data/site" 或 "/data/site/"
            remote: OSS 前缀，如 "site" 或 "site/"

        Returns:
            True 表示同步成功（含无需同步的情况），False 表示过程中出现错误。
        """
        try:
            local_dir = self._normalize_local(local)
            prefix = self._normalize_prefix(remote)

            # 1. 扫描本地文件 → {相对路径: (绝对路径, md5)}
            local_files = self._scan_local(local_dir)
            if not local_files:
                logging.info(f"[sync] 本地目录为空: {local_dir}")
                return True

            # 2. List 远端文件 → {oss_key: etag_md5}
            remote_files = self._list_remote(prefix)

            # 3. 计算需要上传的文件
            to_upload = self._diff(local_files, remote_files, prefix)

            # 4. 计算需要删除的远端多余文件
            local_oss_keys = {
                self._to_oss_key(rel_path, prefix) for rel_path in local_files
            }
            to_delete = [
                oss_key for oss_key in remote_files
                if oss_key not in local_oss_keys
            ]

            if not to_upload and not to_delete:
                logging.info(f"[sync] 已是最新，无需操作 ({len(local_files)} files)")
                return True

            if to_upload:
                logging.info(f"[sync] 需上传 {len(to_upload)}/{len(local_files)} 个文件")
            if to_delete:
                logging.info(f"[sync] 需删除 {len(to_delete)} 个远端多余文件")

            # 5. 逐个上传
            success_count = 0
            for rel_path, abs_path in to_upload:
                oss_key = self._to_oss_key(rel_path, prefix)
                content_type = self._get_content_type(rel_path)
                ok = self._upload(abs_path, oss_key, content_type)
                if ok:
                    success_count += 1
                    logging.info(f"  ✓ {oss_key}  ({content_type})")
                else:
                    logging.info(f"  ✗ {oss_key}  FAILED")

            # 6. 批量删除远端多余文件
            delete_success = 0
            if to_delete:
                # OSS batch_delete 每次最多 1000 个
                BATCH_SIZE = 1000
                for i in range(0, len(to_delete), BATCH_SIZE):
                    batch = to_delete[i:i + BATCH_SIZE]
                    deleted = self._batch_delete(batch)
                    delete_success += deleted
                    for key in batch[:deleted]:
                        logging.info(f"  🗑 {key}")
                    if deleted < len(batch):
                        failed = batch[deleted:]
                        for key in failed:
                            logging.info(f"  ✗ DELETE {key} FAILED")

            total_ok = (success_count == len(to_upload)) and (delete_success == len(to_delete))
            logging.info(f"[sync] 完成: 上传 {success_count}/{len(to_upload)}, "
                         f"删除 {delete_success}/{len(to_delete)}")
            return total_ok

        except Exception as e:
            logging.info(f"[sync] 异常: {e}\n{traceback.format_exc()}")
            return False

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #
    def _batch_delete(self, keys: list[str]) -> int:
        """
        批量删除 OSS 对象，返回成功删除的数量。
        """
        result = self.bucket.batch_delete_objects(keys)
        # BatchDeleteObjectsResult 的成功列表在 result.body 中
        # 但更可靠的方式是直接检查 HTTP 状态码 + 解析
        # oss2 SDK 中实际属性为 result.key_list（已删除的key列表）
        try:
            return len(result.key_list)
        except AttributeError:
            # 兜底：部分旧版本 SDK 用不同属性名
            # 如果 key_list 也不存在，说明全部成功（无报错即成功）
            return len(keys)

    @staticmethod
    def _normalize_local(path: str) -> Path:
        p = Path(path).resolve()
        if not p.is_dir():
            raise ValueError(f"本地路径不是目录: {p}")
        return p

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        """确保 prefix 以 / 结尾且不以 / 开头，空字符串表示根目录。"""
        p = prefix.strip('/')
        return f"{p}/" if p else ""

    def _scan_local(self, local_dir: Path) -> Dict[str, Tuple[Path, str]]:
        """返回 {相对路径(POSIX格式): (绝对路径, md5_hex)}"""
        result: Dict[str, Tuple[Path, str]] = {}
        for file_path in sorted(local_dir.rglob('*')):
            if file_path.is_file():
                rel = file_path.relative_to(local_dir).as_posix()
                md5 = self._file_md5(file_path)
                result[rel] = (file_path, md5)
        return result

    def _list_remote(self, prefix: str) -> Dict[str, str]:
        """List 所有对象，返回 {oss_key: etag_as_md5_hex}"""
        result: Dict[str, str] = {}
        continuation_token = ""
        while True:
            resp = self.bucket.list_objects_v2(
                prefix=prefix,
                max_keys=1000,
                continuation_token=continuation_token,
            )
            for obj in resp.object_list:
                # OSS ETag 就是文件的 MD5（普通上传），去掉引号
                etag = obj.etag.strip('"').lower()
                result[obj.key] = etag

            if not resp.is_truncated:
                break
            continuation_token = resp.next_continuation_token
        return result

    def _diff(self, local_files: Dict[str, Tuple[Path, str]],
              remote_files: Dict[str, str],
              prefix: str) -> list[Tuple[str, Path]]:
        """返回需要上传的 [(rel_path, abs_path), ...]"""
        to_upload = []
        for rel_path, (abs_path, local_md5) in local_files.items():
            oss_key = self._to_oss_key(rel_path, prefix)
            remote_md5 = remote_files.get(oss_key)
            if remote_md5 != local_md5:
                to_upload.append((rel_path, abs_path))
        return to_upload

    @staticmethod
    def _to_oss_key(rel_path: str, prefix: str) -> str:
        """
        生成 OSS key。
        - .html/.htm 文件去掉后缀
        - 拼接 prefix
        """
        lower = rel_path.lower()
        if (lower not in ("index.html", "404.html")) and (lower.endswith('.html') or lower.endswith('.htm')):
            # "test/ok.html" → "test/ok"
            rel_path = rel_path[:rel_path.rfind('.')]
        return f"{prefix}{rel_path}"

    def _get_content_type(self, rel_path: str) -> str:
        """根据原始文件名（去后缀前）推断 Content-Type"""
        ext = Path(rel_path).suffix.lower()
        return self.MIME_MAP.get(ext, 'application/octet-stream')

    def _upload(self, local_path: Path, oss_key: str, content_type: str) -> bool:
        try:
            self.bucket.put_object_from_file(
                oss_key,
                str(local_path),
                headers={'Content-Type': content_type},
            )
            return True
        except Exception as e:
            logging.info(f"    上传失败 {oss_key}: {e}")
            return False

    @staticmethod
    def _file_md5(path: Path) -> str:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
