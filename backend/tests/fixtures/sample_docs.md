# HiSpark Studio for VS Code 知识库

## 支持的芯片型号

HiSpark Studio for VS Code 插件当前支持 BS20、BS21、BS21E、BS22、BS21A、WS63 等芯片型号，支持代码编辑、编译运行、一键烧录、烧录配置、栈分析和镜像分析等功能。

## 工具链下载

HiSpark Studio 提供 Download Toolchain 功能进行工具链的自动下载和安装。点击 Download Toolchain 后，会弹出文件夹选择框。

注意：文件夹选择路径不能包含中文或者空格，否则会有提示框弹出。

工具链下载完成后，会自动在用户环境变量中添加变量名为 HISPARK_TOOL_PATH 的环境变量，变量值为选择的工具链存放位置。

工具链也可以手动通过以下链接下载：
https://hispark-obs.obs.cn-east-3.myhuaweicloud.com/HiSparkStudioToolchain.zip

## SDK 下载

HiSpark Studio 插件当前提供 WS63 和 BS2X 系列的 SDK 下载。

WS63 SDK 在线下载通过 git clone https://gitee.com/HiSpark/fbb_ws63.git 下载。

BS2X SDK 在线下载通过 git clone https://gitee.com/HiSpark/fbb_bs2x.git 下载。

如果没有下载 gitee 代码的权限，会导致下载时间过长最终失败。建议选择空文件夹保存 SDK，避免与其他文件夹相互影响。

## 工程创建

创建工程需要依赖 SDK 软件包。sample 工程当前只支持 WS63 芯片。

## 编译与烧录

COMMANDS 面板提供清除、编译、烧录等功能按钮。状态栏也提供常用功能按钮，包括新建工程、导入工程、工程配置、清除、编译、烧录等功能。

## 栈分析与镜像分析

编译器配置中"为工程分析生成 analyzerJson"选项用于控制编译时是否静态分析工程，分析结果用于栈分析和镜像分析。

自定义 Target 时，如果 Target 为列表中没有的值，调试和栈分析镜像分析功能会受到影响。
