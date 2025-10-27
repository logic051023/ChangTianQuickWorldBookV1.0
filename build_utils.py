#!/usr/bin/env python3
"""
构建工具集 - 配置正确的路径
"""

import os
import sys
import subprocess
import configparser
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BuildError(Exception):
    """构建错误异常"""
    pass


class BuildUtils:
    """构建工具类"""
    
    def __init__(self):
        self.project_root = Path(".")
        self.sdk_dir = Path(os.environ.get('ANDROID_HOME', '/home/runner/android-sdk'))
        
    def configure_buildozer_paths(self):
        """配置Buildozer使用正确的路径"""
        print("=== 配置Buildozer路径 ===")
        
        try:
            # 检查SDK安装
            self._verify_sdk_installation()
            
            # 更新buildozer.spec文件
            self._update_buildozer_spec()
            
            # 创建必要的目录
            self._create_required_directories()
            
            print("✓ Buildozer配置完成")
            
        except Exception as e:
            raise BuildError(f"配置失败: {e}")
    
    def _verify_sdk_installation(self):
        """验证SDK安装"""
        print("=== 验证Android SDK安装 ===")
        
        # 检查SDK目录是否存在
        if not self.sdk_dir.exists():
            raise BuildError(f"Android SDK目录不存在: {self.sdk_dir}")
        
        print(f"Android SDK路径: {self.sdk_dir}")
        
        # 检查sdkmanager
        sdkmanager_path = self.sdk_dir / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        if not sdkmanager_path.exists():
            raise BuildError(f"sdkmanager未找到: {sdkmanager_path}")
        
        print(f"✓ sdkmanager找到: {sdkmanager_path}")
        
        # 检查构建工具
        build_tools_dirs = list(self.sdk_dir.glob("build-tools/*"))
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
        
        return True
    
    def _update_buildozer_spec(self):
        """更新buildozer.spec文件"""
        print("=== 更新buildozer.spec配置 ===")
        
        spec_file = self.project_root / "buildozer.spec"
        if not spec_file.exists():
            raise BuildError("buildozer.spec文件不存在")
        
        config = configparser.ConfigParser()
        config.read(spec_file)
        
        # 确保有buildozer节
        if not config.has_section('buildozer'):
            config.add_section('buildozer')
        
        # 设置正确的sdkmanager路径
        sdkmanager_path = self.sdk_dir / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        config.set('buildozer', 'android.sdk_manager', str(sdkmanager_path))
        
        # 设置SDK目录
        config.set('app', 'android.sdk_dir', str(self.sdk_dir))
        
        # 写入修改
        with open(spec_file, 'w') as f:
            config.write(f)
        
        print("✓ buildozer.spec已更新")
        print(f"  sdkmanager路径: {sdkmanager_path}")
        print(f"  SDK目录: {self.sdk_dir}")
    
    def _create_required_directories(self):
        """创建必要的目录"""
        print("=== 创建必要的目录 ===")
        
        required_dirs = [
            self.project_root / "bin",
            Path.home() / ".buildozer" / "android" / "platform" / "python-for-android",
            self.project_root / ".buildozer_cache"
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ 目录已创建/存在: {directory}")
    
    def run_build(self):
        """执行构建"""
        print("=== 执行APK构建 ===")
        
        try:
            # 设置环境变量
            os.environ['ANDROID_HOME'] = str(self.sdk_dir)
            os.environ['ANDROID_SDK_ROOT'] = str(self.sdk_dir)
            
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
                    "sdkmanager path",
                    "does not exist",
                    "not installed",
                    "error",
                    "failed"
                ]
                
                for phrase in key_phrases:
                    if phrase in content.lower():
                        print(f"发现 '{phrase}' 相关错误:")
                        lines = [line for line in content.split('\n') if phrase in line.lower()]
                        for line in lines[:10]:
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
        print("用法: python build_utils.py [configure-paths|run-build|check-result]")
        sys.exit(1)
    
    command = sys.argv[1]
    utils = BuildUtils()
    
    try:
        if command == "configure-paths":
            utils.configure_buildozer_paths()
        elif command == "run-build":
            success = utils.run_build()
            sys.exit(0 if success else 1)
        elif command == "check-result":
            success = utils.check_build_result()
            sys.exit(0 if success else 1)
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
