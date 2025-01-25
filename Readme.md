# Coze Python 项目

## 项目简介
这是一个用于开发和测试各种Python自动化工具和AI应用的项目集合。目前包含B站视频处理工具等多个子项目，后续会添加更多AI相关的应用和工具。

## 子项目列表

### 1. Bili2Text
B站视频内容提取工具，支持视频下载和音频转文本功能。

#### 主要功能
- 🔍 B站视频搜索与下载
- 🎵 音频提取
- 📝 音频转文本（基于Whisper）
- 📊 完整的日志记录

#### 使用方法
python
from bili2text.main import Bili2Text
初始化
processor = Bili2Text(whisper_model="small")
处理单个视频
result = processor.process_url("https://www.bilibili.com/video/BV1xx411c7mD")
关键词搜索并处理
results = processor.process_keyword("Python教程", max_results=3)

### 2. 更多项目开发中...


## 项目结构
coze-python/
├── bili2text/ # B站视频处理工具
│ ├── core/ # 核心功能模块
│ ├── downloads/ # 下载文件
│ ├── outputs/ # 输出文件
│ └── logs/ # 日志文件
├── future_project1/ # 待开发项目1
├── future_project2/ # 待开发项目2
└── docs/ # 项目文档


## 环境要求
- Python 3.8+
- FFmpeg
- CUDA支持（可选，用于GPU加速）

## 快速开始

1. 克隆项目