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

# 使用兼容的Android版本
android.api = 33
android.minapi = 21
android.ndk = 25b

# 使用兼容的构建工具版本
android.build_tools = 30.0.3

# 架构配置
android.archs = armeabi-v7a

# 构建优化
android.allow_backup = True
android.presplash_color = #FFFFFF

# 允许Buildozer使用我们预安装的SDK
android.skip_download = True
android.accept_sdk_license = True

# SDK路径现在指向Buildozer期望的位置
android.sdk_dir = /home/runner/.buildozer/android/platform/android-sdk

[buildozer]
log_level = 2
warn_on_root = 1

# 构建配置
buildozer.cache_dir = .buildozer_cache
buildozer.parallel_build = True
