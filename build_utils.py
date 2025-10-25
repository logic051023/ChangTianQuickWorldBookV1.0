#!/usr/bin/env python3
"""
构建工具集 - 合并所有构建功能
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


class BuildError(Exception):
    """构建错误异常"""
    pass


class BuildUtils:
    """构建工具类"""

    def __init__(self):
        self.android_home = Path("/home/runner/android-sdk")
        self.ndk_home = Path("/home/runner/android-ndk")
        self.ant_home = Path("/home/runner/ant")

    def setup_environment(self):
        """设置构建环境"""
        try:
            print("=== 设置构建环境 ===")

            # 创建必要的目录
            self._create_directories()

            # 设置环境变量
            self._set_environment_variables()

            # 验证环境
            self._validate_environment()

            print("✓ 环境设置完成")

        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")

    def _create_directories(self):
        """创建必要的目录"""
        dirs = [self.android_home, self.ndk_home, self.ant_home]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"创建目录: {directory}")

    def _set_environment_variables(self):
        """设置环境变量"""
        env_vars = {
            'ANDROID_HOME': str(self.android_home),
            'ANDROID_SDK_ROOT': str(self.android_home),
            'ANDROID_NDK_HOME': str(self.ndk_home),
            'ANDROID_NDK_ROOT': str(self.ndk_home),
        }

        for key, value in env_vars.items():
            os.environ[key] = value
            print(f"设置环境变量: {key}={value}")

    def _validate_environment(self):
        """验证环境设置"""
        print("=== 验证环境 ===")

        # 检查Buildozer
        result = self._run_command("buildozer --version", capture=True)
        if result.returncode != 0:
            raise BuildError("Buildozer未正确安装")

        print("✓ Buildozer验证通过")

    def check_build_result(self):
        """检查构建结果"""
        try:
            print("=== 检查构建结果 ===")

            bin_dir = Path("bin")
            if not bin_dir.exists():
                raise BuildError("构建目录不存在")

            apk_files = list(bin_dir.glob("*.apk"))
            if not apk_files:
                raise BuildError("未找到APK文件")

            for apk in apk_files:
                size_mb = apk.stat().st_size / (1024 * 1024)
                print(f"✓ 找到APK: {apk.name} ({size_mb:.1f} MB)")

            print("✓ 构建成功!")

        except BuildError as e:
            print(f"✗ 构建失败: {e}")

            # 检查构建日志
            self._analyze_build_log()
            sys.exit(1)

    def _analyze_build_log(self):
        """分析构建日志"""
        build_log = Path("build.log")
        if build_log.exists():
            print("=== 构建日志分析 ===")

            with open(build_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 显示最后错误信息
                error_lines = [line for line in lines if 'error' in line.lower()]
                if error_lines:
                    print("错误信息:")
                    for error in error_lines[-10:]:  # 最后10个错误
                        print(f"  {error.strip()}")

    def _run_command(self, command: str, capture: bool = False) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            if capture:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=300
                )
            else:
                result = subprocess.run(command, shell=True, timeout=300)
            return result
        except subprocess.TimeoutExpired:
            raise BuildError(f"命令执行超时: {command}")
        except Exception as e:
            raise BuildError(f"命令执行失败: {command} - {e}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python build_utils.py [setup-environment|check-build-result]")
        sys.exit(1)

    command = sys.argv[1]
    utils = BuildUtils()

    try:
        if command == "setup-environment":
            utils.setup_environment()
        elif command == "check-build-result":
            utils.check_build_result()
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()