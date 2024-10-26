
import os

# ---------------------------------------------------------------------#
#   配置参数
# ---------------------------------------------------------------------#
env_name = 'py_rppg'
# 程序主文件
py_file = "main.py"
# 程序图标
ico_file = "logo.ico"
# 是否打包成一个exe文件
single_exe = True
# 是否不显示控制台
no_console = False
# 添加资源文件或文件夹
extra_data = []
# 程序名字
name = "rPPGCollectTool"

# ---------------------------------------------------------------------#
#   构建打包代码
# ---------------------------------------------------------------------#
cmd_code = f"activate {env_name} && pyinstaller.exe"
if single_exe:
    cmd_code += ' -F'
else:
    cmd_code += ' -D'
if no_console:
    cmd_code += ' -w'
else:
    cmd_code += ' -c'
if len(ico_file) > 0:
    cmd_code += f' -i {ico_file}'

cmd_code += f' -n {name}'

for data in extra_data:
    cmd_code += f' --add-data "{data}";"{data}"'
# 在打包之前清理之前生成的临时文件
cmd_code += ' --clean'
cmd_code += f" {py_file}"
os.system(cmd_code)

print("打包完成！")
