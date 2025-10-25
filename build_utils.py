#!/usr/bin/env python3
"""
构建工具集 - 修复AIDL和SDK路径问题
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
        
    def setup_build_environment(self):
        """设置构建环境"""
        print("=== 设置构建环境 ===")
        
        try:
            # 确保必要的目录存在
            (self.project_root / "bin").mkdir(exist_ok=True)
            
            # 检查Android SDK
            self._check_android_sdk()
            
            # 配置Buildozer环境
            self._setup_buildozer_environment()
            
            # 验证环境
            self._validate_environment()
            
            print("✓ 构建环境设置完成")
            
        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")
    
    def _check_android_sdk(self):
        """检查Android SDK安装"""
        print("=== 检查Android SDK ===")
        
        if not self.android_home.exists():
            raise BuildError(f"Android SDK目录不存在: {self.android_home}")
        
        print(f"Android SDK路径: {self.android_home}")
        
        # 检查构建工具
        build_tools_dirs = list(self.android_home.glob("build-tools/*"))
        if not build_tools_dirs:
            raise BuildError("未找到Android构建工具，请先安装构建工具")
        
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
                # 确保AIDL可执行
                aidl_path.chmod(0o755)
                break
        
        if not aidl_found:
            # 尝试在其他位置查找
            print("在构建工具目录中未找到AIDL，搜索整个SDK...")
            result = subprocess.run(
                f"find {self.android_home} -name 'aidl' -type f 2>/dev/null",
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                print("在其他位置找到的AIDL:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        print(f"  - {line}")
                        aidl_found = True
            else:
                raise BuildError("AIDL工具未找到，请确保Android构建工具已正确安装")
    
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
            # 尝试复制
            print("尝试复制SDK...")
            try:
                shutil.copytree(self.android_home, sdk_link)
                print("✓ SDK复制成功")
            except Exception as e2:
                print(f"✗ SDK复制失败: {e2}")
    
    def _validate_environment(self):
        """验证环境设置"""
        print("=== 验证环境 ===")
        
        # 检查Buildozer
        result = self._run_command("buildozer --version", capture=True)
        if result.returncode != 0:
            raise BuildError("Buildozer未正确安装")
        print("✓ Buildozer验证通过")
        
        # 检查Android SDK
        if not self.android_home.exists():
            raise BuildError("Android SDK路径不存在")
        print("✓ Android SDK路径验证通过")
        
        # 检查构建工具
        build_tools = list(self.android_home.glob("build-tools/*"))
        if not build_tools:
            raise BuildError("未找到构建工具")
        print(f"✓ 构建工具验证通过: {[bt.name for bt in build_tools]}")
    
    def run_build(self):
        """执行构建"""
        print("=== 执行APK构建 ===")
        
        try:
            # 设置环境变量
            os.environ['ANDROID_HOME'] = str(self.android_home)
            os.environ['ANDROID_SDK_ROOT'] = str(self.android_home)
            
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
                
                # 查找AIDL相关错误
                if "aidl" in content.lower():
                    print("发现AIDL相关错误:")
                    aidl_lines = [line for line in content.split('\n') if 'aidl' in line.lower()]
                    for line in aidl_lines[:10]:
                        print(f"  {line}")
                
                # 查找许可证相关错误
                if "license" in content.lower():
                    print("发现许可证相关错误:")
                    license_lines = [line for line in content.split('\n') if 'license' in line.lower()]
                    for line in license_lines[:10]:
                        print(f"  {line}")
                
                # 显示最后的关键错误
                print("最后的关键错误:")
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
        print("用法: python build_utils.py [setup-environment|run-build|check-result]")
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
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
