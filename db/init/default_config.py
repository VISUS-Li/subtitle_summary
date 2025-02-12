# db/init/default_configs.py

DEFAULT_CONFIGS = {
    # YouTube下载配置
    "youtube_download": {
        "category": "download",
        "configs": {
            "base_opts": {
                "value": {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "no_warnings": True,
                    "extract_audio": True,
                    "sleep_interval_requests": 1,
                    "ratelimit": 900000,
                    "retries": 2,
                    "fragment_retries": 2,
                    "retry_sleep": 10,
                },
                "description": "YouTube下载器基础选项配置"
            },
            "info_opts": {
                "value": {
                    "dump_single_json": True,
                    "quiet": True,
                    "no_warnings": True,
                },
                "description": "视频信息获取选项配置"
            },
            "subtitle_opts": {
                "value": {
                    "skip_download": True,
                    "write_auto_sub": True,
                    "sub_lang": "zh-Hans,en",
                },
                "description": "字幕下载选项配置"
            },
            "audio_opts": {
                "value": {
                    "format": "bestaudio/best",
                    "extract_audio": True,
                    "audio_format": "mp3",
                    "audio_quality": 0,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                },
                "description": "音频下载选项配置"
            },
            "cookie_data": {
                "value": {},
                "description": "YouTube下载时的cookies"
            }
        }
    },

    # Bilibili下载配置
    "bilibili_download": {
        "category": "download",
        "configs": {
            "base_opts": {
                "value": {
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }],
                    "quiet": True,
                    "sleep_interval_requests": 3,
                    "ratelimit": 800000,
                    "retries": 3,
                    "fragment_retries": 3,
                    "retry_sleep": 5
                },
                "description": "B站下载器基础选项配置"
            },
            "sessdata": {
                "value": "",
                "description": "B站登录凭证SESSDATA"
            },
            "bili_jct": {
                "value": "",
                "description": "B站登录凭证bili_jct"
            },
            "buvid3": {
                "value": "",
                "description": "B站登录凭证buvid3"
            }
        }
    },

    # Whisper模型配置
    "whisper": {
        "category": "model",
        "configs": {
            "model_name": {
                "value": "base",
                "description": "Whisper模型名称,可选:tiny/base/small/medium/large"
            },
            "language": {
                "value": "zh",
                "description": "识别的目标语言"
            },
            "prompt": {
                "value": "",
                "description": "识别提示词"
            }
        }
    },

    # 系统配置
    "system": {
        "category": "system",
        "configs": {
            "max_retries": {
                "value": 3,
                "description": "最大重试次数"
            },
            "retry_delay": {
                "value": 5,
                "description": "重试间隔时间(秒)"
            },
            "max_concurrent_downloads": {
                "value": 3,
                "description": "最大并发下载数"
            },
            "max_concurrent_transcriptions": {
                "value": 2,
                "description": "最大并发转录数"
            },
            "download_dir": {
                "value": "downloads",
                "description": "下载文件目录"
            },
            "output_dir": {
                "value": "outputs",
                "description": "输出文件目录"
            },
            "temp_dir": {
                "value": "temp",
                "description": "临时文件目录"
            },
            "log_dir": {
                "value": "logs",
                "description": "日志文件目录"
            }
        }
    }
}
