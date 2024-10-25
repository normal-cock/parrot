


## 设置完src之后，currentTime不起作用的问题

初次设置完src时，调用完play，会重置currentTime。因为在data为load好之前调用currentTime都不会成功所以即使在play之后调用currentTime也不太可行。

可行的方式：
1. 在loadeddata回调中额外调用currentTime
2. 在timeupdate中，控制时间。

## 移动端和pc的差异


m3u8的支持
    currentTime在移动端不起作用。换成mp3就可以了。可以尝试hls.js库
    `player.load`函数貌似只在移动端起作用
    `player.duration()`也是空的
    报错的函数需要先手动播放后，才能调用。通常，用手动点击按钮播放一次后，才能调用报错的函数。这是浏览器的安全保护机制，防止自动播放
        [Error] Unhandled Promise Rejection: NotAllowedError: The request is not allowed by the user agent or the platform in the current context, possibly because the user denied permission.
        play