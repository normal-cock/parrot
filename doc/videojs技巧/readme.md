


## 设置完src之后，currentTime不起作用的问题

初次设置完src时，调用完play，会重置currentTime。因为在data为load好之前调用currentTime都不会成功所以即使在play之后调用currentTime也不太可行。

可行的方式：
1. 在loadeddata回调中额外调用currentTime
2. 在timeupdate中，控制时间。