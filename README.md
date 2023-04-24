# Xosc-modifier
## Info
Author: Harvey Miao  
Python Version: 3.8.15  
概括: 基于Openscenario 1.x协议，对已有的场景文件进行批量修改或泛化  
## 项目结构
- src: 可执行脚本文件所在目录
- test: 存储测试用文件，包括: agents.json，主车_VIO.json, 主车_J5.json
- image: 存储README文件用到的截图
- modifier.exe: 可执行文件
## 支持功能
### 批量修改
1. 主车速度
2. 结束时间
3. 对手车模型
4. 主车模型 (Bounding Box需要手动输入)
### 场景泛化
1. 主车速度
2. 偏置率（仅限C2C场景）
## 使用说明
1. 首先把51simone中导出的场景文件解压缩  
支持如下图所示的文件夹树结构  
![树状图](./image/file-tree.png "tree")
2. 将config.json文件和modifer.py/modifier.exe放置在同一目录下
3. 配置config.json文件
3. 运行 ``python3 modifier.py`` 或打开目录下的modifier.exe,
## 注意事项
1. 运行环境为Windows时，config.json中的output_path需要使用windows的格式，例：``.\\results\\foo``
## 备注
- 打包指令：``pyinstaller.exe -F -c -i .\image\modifier.ico .\src\modifier.py`` （Windows powershell）