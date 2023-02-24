---
title: 一些Python编程技巧
category: 学习笔记
tags: 编程， Python
---
<!--more-->

#### 尽量使用就地操作。

Python的某些对象的同一种操作有多种方法，如对一个list进行排序，可以使用内置函数sorted和list.sort方法。不同的是，后者返回值是none，这以为排序操作是原址进行的，而不会像前一种一样会复制一个list出来，因而也会节省一些内存。

用返回 None 来表示就地改动，这种做法其实有个弊端，那就是调用者无法将其串联起来，形成类似JavaScript常见的链式操作。Python中的str对象却有些特殊，它的所有方法都可以串联起来调用，从而形成连贯接口。当然究其原因，是因为str在Python中是一个不可变对象，就地改动也就行不通了。

#### 尝试使用扁平序列

Python中的序列包括list、tuple、str、bytes、bytearray等，可以大致分为两类，就是可以包含不同对象的容器类型，如list、tuple等，和只能包含同一种对象的扁平类型，如str、bytes、bytearray、memoryview 和 array.array等。

容器序列存放的是它们所包含的任意类型的对象的引用，而扁平序列里存放的是值而不是引用。扁平序列一段连续的内存空间，所以更加紧凑，在绝大多数的情况下，它的操作效率是远高于容器序列的。

比如，当需要创建一个只包含数字的列表，那么 array.array 比 list 高效多了。数组几乎支持所有list、tuple等可变序列所支持的操作，包括.pop、.insert 和 .extend等。另外，数组还提供从文件读取和存入文件的更快的方法，如.frombytes 和 .tofile。

同样还有memoryview，亦即内存视图。它是一个内置类，它能让用户在不复制内容的情况下操作同一个数组的不同切片。它让你在不需要复制内容的前提下， 在数据结构之间共享内存。其中数据结构可以是任何形式，比如 PIL 图片、SQLite 数据库和 NumPy 的数组等。这个功能在处理大型数据集合的时候非常重要。memoryview.cast 的概念跟数组模块类似，能用不同的方式读写同一块内存数据，而且内容字节不会随意移动。这听上去又跟 C 语言中类型转换的概念差不多。memoryview.cast 会把同一块内存里的内容打包成一个全新的 memoryview 对象给你。

内存视图是一个很微妙的类，要想熟练使用，必须对内存对其之类的计算机基础知识有扎实的掌握。下面是一个实例：
```
numbers = array.array('h', [-2, -1, 0, 1, 2])
memv = memoryview(numbers)
len(memv)
>>>: 5
memv[0]
>>>: -2

memv_oct = memv.cast('B')
memv_oct.tolist()
>>>: [254, 255, 255, 255, 0, 0, 1, 0, 2, 0]
memv_oct[5] = 4
numbers
>>>: array('h', [-2, -1, 1024, 1, 2])
```

这里利用含有 5 个短整型有符号整数的数组(类型码是 'h'，对应C语言2字节有符号整数，32位系统中通常为short int)创建一个 memoryview。而此时，5 个元素跟数组里的没有区别。接下来把 memv 里的内容转换成 'B' 类型，也就是无符号字符类型，绑定到memv_oct。然后把memv_oct中位于位置 5 的字节赋值成 4。因为把占 2 个字节的整数的高位字节改成了 4，所以这个有符号整数的值就变成了 1024。再转换回去，得到最终的结果。利用 memoryview 和 struct 来操作二进制序列，不仅可以实现强大的功能，而且在时间效率和空间利用率上也是十分的高效。

#### 在合适的场合使用具名元组

Python中的映射类型采用了哈希表存储索引，一般来讲会消耗较多的空间，相比于数组或者list、tuple等类型，比较不经济。而在某些情景下，比如已知一个树形结构的字段的范围，就可以使用具名元组来替代dict。

collections.namedtuple 是一个工厂函数，它可以用来构建一个带字段名的元组和一个有名字的类。用 namedtuple 构建的类的实例所消耗的内存跟元组是一样的，因为字段名都被存在对应的类里面。这个实例甚至跟普通的对象实例比起来也要小一些，因为具名元组的实例没有```__dict__```，而其他对象一般需要```__dict__```来存放这些实例的属性。

在《流畅的Python》中是这样使用具名元组的:
```
Card = collections.namedtuple('Card', ['rank', 'suit'])
```
下面展示了使用具名元组来记录一个城市的信息。
```
from collections import namedtuple
City = namedtuple('City', 'name country population coordinates')
tokyo = City('Tokyo', 'JP', 36.933, (35.689722, 139.691667))

tokyo
>>>: City(name='Tokyo', country='JP', population=36.933, coordinates=(35.689722, 139.691667))

tokyo.population
>>>: 36.933

tokyo.coordinates
>>>: (35.689722, 139.691667)

tokyo[1]
>>>: 'JP'
```

创建一个具名元组需要两个参数，一个是类名，另一个是类的各个字段的名字。后者可以是由数个字符串组成的可迭代对象，或者是由空格分隔开的字段名组成的字符串。存放在对应字段里的数据要以一串参数的形式传入到构造函数中，这与元组不同的是，后者的构造函数却只接受单一的可迭代对象。然后就可以通过字段名或者位置来获取一个字段的信息。

除了从普通元组那里继承来的属性之外，具名元组还有一些自己专有的属性：

* _fields: 返回一个包含这个类所有字段名称的元组
* _make(): 通过接受一个可迭代对象来生成这个类的一个实例，它的作用跟City(*delhi_data) 是一样的
* _asdict() 把具名元组以 collections.OrderedDict 的形式返回，我们可以利用它来把元组里的信息友好地呈现出来

使用具名元组在处理大数据量的场景下，能够节省大量内存。但之所以说在合适的场合使用具名元组，是因为具名元组并不能完全替代映射类型。一般来讲，映射类型对单个元素的访问速度极高，只要内存里放得下，随机访问的时间效率趋近O(1)。而具名元组这种序列在随机访问下，表现就比较糟糕，例如做" in "操作时，最坏需要把序列中所有的元素都遍历一遍，时间复杂度为O(n)。所以时间重要还是空间重要，这是一个权衡。

#### 泛映射类型的效率

dict是Python中最常见的映射类型，而且标准库里的所有映射类型都是利用 dict 来实现的，因此它们有个共同的限制，即只有可散列的数据类型才能用作这些映射里的键，也叫可哈希类型。可散列对象的定义包含两个条件，一是整个生命周期中它的散列值不变，第二个条件是这个对象需要实现 ```__hash__```() 方法来获取哈希值，并实现```__qe__```()方法和其他值做对比。如果两个可散列对象是相等的，那么它们的散列值一定是一样的。因此，不仅常见的原子不可变类型如str、bytes和数值类型可以作为dict的键，所有包含的元素都是可散列对象的tuple同样可以作为dict的键，如(1, 2, 3)等。

##### 处理找不到的键
* 使用```__missing__```

	所有的映射类型在处理找不到的键的时候，都会调用```__missing__```方法。也就是说，如果有一个类继承了 dict，然后这个继承类提供了 __missing__ 方 法，那么在 ```__getitem__``` 碰到找不到的键的时候，Python 就会自动调用它，而不是抛出一个 KeyError 异常。

	```__missing__``` 方法只会被 ```__getitem__``` 调用(比如在表达式 d[k] 中)。提供 ```__missing__``` 方法对 get 或者 ```__contains__```(in 运算符会用到这个方法)这些方法的使用没有影响。例如：
	```
	class UserDict(dict):
		def __missing__(self, key):
			print key
			return 0

	d = UserDict()
	print d["k"]
	>>>: k
	0

	print d.get("k")
	>>>: None
	```

* 使用setdefault

	dict中访问元素的方法有两种，一种是直接使用下标形如d[k]来访问，另一种是使用d.get(k)。第一种方法的效率更高，所以在需要大量访问dict元素的场合，这种形式能够节约大量的开销。然而这种方式在遇到找不到该键的时候会抛出恼人的KeyError异常。所以在不能确保key是否包含在d中的时候，一般更倾向于使用后者。

	下例是一个常见的操作：
```
# d={...: ... }
data = d.get("data", [])
data.append("x...")
d["data"] = data
```
这完全可以改写成：
```
d.setdefault("data", []).append("x...")
```
setdefault的作用是获取键为"data"的元素，如果不存在则设置为[]，再将该[]返回。这种写法不仅更紧凑，而且减少了一次对dict的访问。

对于dict和list等的效率，《流畅的Python》中做了一个测试，在 core i7的CPU上，分别从含有1000个键、1万个、……1千万个键的dict中，取1000个元素，测试消耗时间。在只有1000个键的dict中取1000个元素，平均每个消耗202微秒，在1千万个键的dict中取1000个元素，平均每个也只消耗了337微秒。而换成list之后，花费分别变为20毫秒和97秒。而理解了dict使用哈希表来实现的事实之后，也就不奇怪了。

所以对于dict有以下特性：

* 键必须可哈希。需要注意的是，所有由用户自定义的对象默认都是可散列的，因为它们的散列值由 id() 来获取，而且它们 都是不相等的
* 字典在内存上的开销巨大。由于字典使用了散列表，而散列表又必须是稀疏的，这导致它在空间上的效率低下，所以字典并不是在任何时候都是合适的
* 键查询很快。字典类型有着巨大的内存开销，但保证了数据量呈数量级的规模增长时，查询时间的开销仅仅常数级增多
* 键的次序取决于添加顺序。当往 dict 里添加新键而又发生散列冲突的时候，新键可能会被安排存放到另一个位置，从而造成键值得无序
* 往字典里添加新键可能会改变已有键的顺序。无论何时往字典里添加新的键，Python 解释器都可能做出为字典扩容的决定。扩容导致的结果就是要新建一个更大的散列表，并把字典里已有的元素添加到新表里，这个过程中可能会发生新的散列冲突，导致新散列表中键的次序变化