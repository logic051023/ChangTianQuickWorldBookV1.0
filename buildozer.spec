[app]
title = 长天快速世界书
package.name = changtianworldbook
package.domain = org.changtian
version = 1.0.0
source.dir = .
source.main = main.py
requirements = python3,kivy==2.2.1
orientation = portrait
android.permissions = INTERNET

# 使用现代Android版本
android.api = 33
android.minapi = 21
android.ndk = 25b

# 修复架构配置 - 使用正确的archs参数
android.archs = armeabi-v7a,arm64-v8a

# 构建工具版本
android.build_tools = 34.0.0

# 构建优化
android.allow_backup = True
android.presplash_color = #FFFFFF

[buildozer]
log_level = 2
warn_on_root = 1

# 构建配置
buildozer.cache_dir = .buildozer_cache
buildozer.parallel_build = True
