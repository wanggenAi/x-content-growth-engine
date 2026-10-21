# 已核对的发布候选（未提交X）

唯一正式队列话题：eMudhra极弱私钥。三版均过现有审核，最终只选A，三个版本不是三个独立可发帖子。

## A

给网站发安全证书的机构，有把私钥竟然是4。

Scott Helme在10月20日文章里核对eMudhra证书：本该是384位随机数，实际取值小到一个字节就装得下。另两把是56和115。

格式检查都过。Chrome和Firefox已直接封锁相关中间证书。

https://scotthelme.co.uk/eight-bits-of-trust-emudhras-ca-keys-cracked-in-milliseconds/

保留：第一句交代这不是个人密码；384位和浏览器已拦截守住边界。缺点是术语仍有门槛，末句不承担新的安全建议。

## B

还以为漏了一长串数字。没有，私钥就是4。

Scott Helme在10月20日文章中给出的eMudhra私钥，还有56和115。

Chrome和Firefox已直接封锁相关中间证书。最离谱的是，证书格式检查还全都过了。

https://scotthelme.co.uk/eight-bits-of-trust-emudhras-ca-keys-cracked-in-milliseconds/

未选：口语更松，但开头要读两句才懂是什么私钥，省掉384位后机制信息减少。

## C

证书格式检查，全过了。私钥，却是4。

这次的问题，外观上看不出来。Scott Helme在10月20日文章里核对eMudhra证书发现：本应是384位随机数，实际取值小到一个字节就装得下。

Chrome和Firefox已直接封锁相关中间证书。

https://scotthelme.co.uk/eight-bits-of-trust-emudhras-ca-keys-cracked-in-milliseconds/

未选：合规与强度的反差更尖锐，但开头未先解释证书机构，末句容易像套路总结。

限制：仍有私钥、384位等技术门槛；大众代入不如生活题材。阅读兴趣是编辑假设，不是流量结果。Chrome/Firefox边界已重新收紧，未声称实际攻击或亲身复现。

历史新闻摘要对照：研究者近日披露，eMudhra部分中间证书存在弱私钥问题，相关厂商已采取措施。这一事件说明安全检查需要更加完善。
