# 使用方法：
- `python3 main.py -f /tmp/p2p_test/log/xtop.log -d database_name -a 161.35.114.185:9010`
- 其中 -f 加日志路径 ， -a 加server的ip:port -d 为分组名&&进入数据库名称

# 编译
## 安装pyinstaller
    # python3 -m pip install -U pip
    # python3 -m pip install pyinstaller
## 编译
    # ./build.sh
    ***生成的二进制文件位于根目录下的dist/main***
    ***注意一定要在工程根目录执行这个命令***

# 下载最新的归档二进制包
## 安装gh
    # sudo yum install -y epel-release
    # sudo yum install -y snapd
    # sudo systemctl enable --now snapd.socket
    # sudo ln -s /var/lib/snapd/snap /snap
    # sudo snap install gh
## 配置环境
    # git init && git remote add origin git@github.com:Alipipe/top-dw-agent.git
## 鉴权并下载最新一次编译成功的归档二进制包
    # gh auth login --with-token < token
    # gh run list --repo=Alipipe/top-dw-agent|grep success|head -n1|awk '{print $7}'|xargs -I {} bash -c 'gh run download {} -n main --repo=Alipipe/top-dw-agent'
#### token文件包含一个授权码，授权码内容生成网站 https://github.com/settings/tokens

