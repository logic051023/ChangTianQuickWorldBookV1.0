#!/usr/bin/env python3
"""
构建工具集 - 修复SDK安装问题
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
        self.android_home = Path(os.environ.get('ANDROID_HOME', '/home/runner/android-sdk'))
        
    def verify_sdk_installation(self):
        """验证SDK安装"""
        print("=== 验证Android SDK安装 ===")
        
        # 检查SDK目录是否存在
        if not self.android_home.exists():
            raise BuildError(f"Android SDK目录不存在: {self.android_home}")
        
        print(f"Android SDK路径: {self.android_home}")
        
        # 检查sdkmanager
        sdkmanager_path = self.android_home / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        if not sdkmanager_path.exists():
            # 尝试在其他位置查找
            found_sdkmanager = False
            for possible_path in self.android_home.glob("**/sdkmanager"):
                if possible_path.is_file():
                    print(f"找到sdkmanager: {possible_path}")
                    found_sdkmanager = True
                    break
            
            if not found_sdkmanager:
                raise BuildError("sdkmanager未找到，Android SDK安装失败")
        else:
            print(f"✓ sdkmanager找到: {sdkmanager_path}")
            
            # 确保sdkmanager可执行
            try:
                sdkmanager_path.chmod(0o755)
                print("✓ sdkmanager设置为可执行")
            except Exception as e:
                print(f"⚠ 无法设置sdkmanager可执行: {e}")
        
        # 检查构建工具
        build_tools_dirs = list(self.android_home.glob("build-tools/*"))
        if not build_tools_dirs:
            print("⚠ 警告: 未找到Android构建工具")
        else:
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
                try:
                    aidl_path.chmod(0o755)
                    print("✓ AIDL工具设置为可执行")
                except Exception as e:
                    print(f"⚠ 无法设置AIDL可执行: {e}")
                break
        
        if not aidl_found:
            print("⚠ 警告: 未找到AIDL工具")
            
        return True
    
    def setup_build_environment(self):
        """设置构建环境"""
        print("=== 设置构建环境 ===")
        
        try:
            # 确保必要的目录存在
            (self.project_root / "bin").mkdir(exist_ok=True)
            
            # 验证SDK安装
            self.verify_sdk_installation()
            
            # 配置Buildozer环境
            self._setup_buildozer_environment()
            
            print("✓ 构建环境设置完成")
            
        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")
    
    def _setup_buildozer_environment(self):
        """配置Buildozer环境"""
        print("=== 配置Buildozer环境 ===")
        
        buildozer_platform_dir = Path.home() / ".buildozer" / "android" / "platform"
        buildozer_platform_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建指向系统SDK的符号链接
        sdk_link = buildozer_platform_dir / "android-sdk"
        if sdk_link.exists():
            if sdk_link.is_symlink():
                sdk_link.unlink()
            else:
                shutil.rmtree(sdk_link)
        
        try:
            sdk_link.symlink_to(self.android_home)
            print(f"✓ 创建SDK符号链接: {sdk_link} -> {self.android_home}")
        except Exception as e:
            print(f"✗ 创建符号链接失败: {e}")
            # 如果符号链接失败，尝试使用环境变量
            print("将依赖环境变量设置")
    
    def run_build(self):
        """执行构建"""
        print("=== 执行APK构建 ===")
        
        try:
            # 设置环境变量
            os.environ['ANDROID_HOME'] = str(self.android_home)
            os.environ['ANDROID_SDK_ROOT'] = str(self.android_home)
            
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
                
                # 确保APK在bin目录中
                if "bin" not in str(apk):
                    bin_dir = self.project_root / "bin"
                    bin_dir.mkdir(exist_ok=True)
                    target_apk = bin_dir / apk.name
                    shutil.copy2(apk, target_apk)
                    print(f"  已复制到: {target_apk}")
            
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
                
                # 查找SDK相关错误
                if "sdkmanager" in content.lower():
                    print("发现sdkmanager相关错误:")
                    sdk_lines = [line for line in content.split('\n') if 'sdkmanager' in line.lower()]
                    for line in sdk_lines[:10]:
                        print(f"  {line}")
                
                # 查找AIDL相关错误
                if "aidl" in content.lower():
                    print("发现AIDL相关错误:")
                    aidl_lines = [line for line in content.split('\n') if 'aidl' in line.lower()]
                    for line in aidl_lines[:10]:
                        print(f"  {line}")
                
                # 显示最后的错误
                print("最后的错误信息:")
                error_lines = [line for line in content.split('\n') if any(keyword in line.lower() for keyword in ['error', 'failed'])]
                for line in error_lines[-15:]:
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
        print("用法: python build_utils.py [setup-environment|run-build|check-result|verify-sdk]")
        sys.exit(1)
    
    command = sys.argv[1]
    utils = BuildUtils()
    
    try:
        if command == "setup-environment":
            utils.setup_build_environment()
        elif command == "run-build":
            success = utils.run_build()
            sys.exit(0 if success else 1)
        elif command == "check-result":
            success = utils.check_build_result()
            sys.exit(0 if success else 1)
        elif command == "verify-sdk":
            utils.verify_sdk_installation()
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
