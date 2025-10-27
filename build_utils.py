#!/usr/bin/env python3
"""
构建工具集 - 简化版本，直接使用Buildozer期望的位置
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BuildError(Exception):
    """构建错误异常"""
    pass


class BuildUtils:
    """构建工具类"""
    
    def __init__(self):
        self.project_root = Path(".")
        self.buildozer_sdk_dir = Path.home() / ".buildozer" / "android" / "platform" / "android-sdk"
        
    def verify_environment(self):
        """验证环境设置"""
        print("=== 验证构建环境 ===")
        
        # 检查Buildozer
        result = self._run_command("buildozer --version", capture=True)
        if result.returncode != 0:
            raise BuildError("Buildozer未正确安装")
        print("✓ Buildozer验证通过")
        
        # 检查Android SDK
        if not self.buildozer_sdk_dir.exists():
            raise BuildError(f"Android SDK目录不存在: {self.buildozer_sdk_dir}")
        print(f"✓ Android SDK目录存在: {self.buildozer_sdk_dir}")
        
        # 检查sdkmanager
        sdkmanager_path = self.buildozer_sdk_dir / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        if not sdkmanager_path.exists():
            raise BuildError(f"sdkmanager未找到: {sdkmanager_path}")
        print(f"✓ sdkmanager找到: {sdkmanager_path}")
        
        # 检查构建工具
        build_tools_dirs = list(self.buildozer_sdk_dir.glob("build-tools/*"))
        if not build_tools_dirs:
            raise BuildError("未找到Android构建工具")
        
        print("找到的构建工具版本:")
        for tool_dir in build_tools_dirs:
            print(f"  - {tool_dir.name}")
        
        # 检查AIDL工具
        aidl_found = False
        for tool_dir in build_tools_dirs:
            aidl_path = tool_dir / "aidl"
            if aidl_path.exists():
                print(f"✓ 找到AIDL工具: {aidl_path}")
                aidl_found = True
                break
        
        if not aidl_found:
            raise BuildError("AIDL工具未找到")
        
        print("✓ 环境验证完成")
    
    def setup_environment(self):
        """设置构建环境"""
        print("=== 设置构建环境 ===")
        
        try:
            # 确保必要的目录存在
            (self.project_root / "bin").mkdir(exist_ok=True)
            
            # 验证环境
            self.verify_environment()
            
            print("✓ 构建环境设置完成")
            
        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")
    
    def run_build(self):
        """执行构建"""
        print("=== 执行APK构建 ===")
        
        try:
            # 设置环境变量
            os.environ['ANDROID_HOME'] = str(self.buildozer_sdk_dir)
            os.environ['ANDROID_SDK_ROOT'] = str(self.buildozer_sdk_dir)
            
            print(f"环境变量设置: ANDROID_HOME={os.environ.get('ANDROID_HOME')}")
            print(f"环境变量设置: ANDROID_SDK_ROOT={os.environ.get('ANDROID_SDK_ROOT')}")
            
            # 清理之前的构建
            print("清理构建环境...")
            self._run_command("buildozer android clean", check=False)
            
            # 执行构建
            print("开始构建APK...")
            result = self._run_command(
                "buildozer -v android debug", 
                check=False,
                capture=False
            )
            
            if result.returncode == 0:
                print("✓ 构建成功完成")
                return True
            else:
                print(f"✗ 构建失败，退出码: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"✗ 构建过程出错: {e}")
            return False
    
    def check_build_result(self):
        """检查构建结果"""
        try:
            print("=== 检查构建结果 ===")
            
            # 在多个可能的位置查找APK
            apk_locations = [
                self.project_root / "bin",
                self.project_root / ".buildozer" / "android" / "platform" / "build" / "dists",
                self.project_root
            ]
            
            apk_files = []
            for location in apk_locations:
                if location.exists():
                    found = list(location.glob("**/*.apk"))
                    apk_files.extend(found)
                    if found:
                        print(f"在 {location} 找到 {len(found)} 个APK文件")
            
            if not apk_files:
                raise BuildError("未找到APK文件")
            
            for apk in apk_files:
                size_mb = apk.stat().st_size / (1024 * 1024)
                print(f"✓ 找到APK: {apk.relative_to(self.project_root)} ({size_mb:.1f} MB)")
            
            print("✓ 构建成功!")
            return True
            
        except BuildError as e:
            print(f"✗ 构建失败: {e}")
            
            # 分析构建日志
            self._analyze_build_log()
            return False
    
    def _analyze_build_log(self):
        """分析构建日志"""
        build_log = self.project_root / "build.log"
        if build_log.exists():
            print("=== 构建日志分析 ===")
            
            with open(build_log, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 查找关键错误
                key_phrases = [
                    "error",
                    "failed", 
                    "not found",
                    "no such file",
                    "cannot find",
                    "sdkmanager",
                    "aidl"
                ]
                
                for phrase in key_phrases:
                    if phrase in content.lower():
                        print(f"发现 '{phrase}' 相关错误:")
                        lines = [line for line in content.split('\n') if phrase in line.lower()]
                        for line in lines[:5]:
                            print(f"  {line}")
                
                # 显示最后的错误
                print("最后的错误信息:")
                error_lines = [line for line in content.split('\n') if any(keyword in line.lower() for keyword in ['error', 'failed'])]
                for line in error_lines[-10:]:
                    print(f"  {line}")
        else:
            print("无构建日志文件")
    
    def _run_command(self, command: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            print(f"执行命令: {command}")
            
            if capture:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, 
                    timeout=1800, cwd=self.project_root
                )
                if result.stdout:
                    print(f"输出: {result.stdout[-500:]}")
                if result.stderr:
                    print(f"错误: {result.stderr[-500:]}")
            else:
                result = subprocess.run(
                    command, shell=True, timeout=1800, cwd=self.project_root
                )
            
            if check and result.returncode != 0:
                raise BuildError(f"命令执行失败: {command} (退出码: {result.returncode})")
                
            return result
            
        except subprocess.TimeoutExpired:
            raise BuildError(f"命令执行超时: {command}")
        except Exception as e:
            raise BuildError(f"命令执行失败: {command} - {e}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python build_utils.py [setup-environment|run-build|check-result|verify-env]")
        sys.exit(1)
    
    command = sys.argv[1]
    utils = BuildUtils()
    
    try:
        if command == "setup-environment":
            utils.setup_environment()
        elif command == "run-build":
            success = utils.run_build()
            sys.exit(0 if success else 1)
        elif command == "check-result":
            success = utils.check_build_result()
            sys.exit(0 if success else 1)
        elif command == "verify-env":
            utils.verify_environment()
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
