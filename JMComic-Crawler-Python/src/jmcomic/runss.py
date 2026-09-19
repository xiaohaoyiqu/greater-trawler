import jmcomic

# 创建配置对象
option = jmcomic.create_option_by_file('D:\\xuexi\\python\\JMComic-Crawler-Python-master\\src\\option.yml')
# 使用option对象来下载本子
jmcomic.download_album(1091443, option)
# 等价写法: option.download_album(422866)
