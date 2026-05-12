import os
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentConverter:
    """
    针对 macOS 优化的文档转换服务。
    利用系统级 Office 应用 (Word/Pages) 实现高质量 PDF 导出。
    """

    @staticmethod
    def docx_to_pdf(input_path: str, output_path: Optional[str] = None) -> str:
        """
        将 .docx 转换为 .pdf。
        如果未提供 output_path，则在同一目录下生成同名 .pdf。
        """
        input_path = os.path.abspath(input_path)
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + ".pdf"
        output_path = os.path.abspath(output_path)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # 尝试使用 Word 转换 (最高优先级，排版最准确)
        success = DocumentConverter._convert_with_word(input_path, output_path)
        
        if not success:
            logger.warning("Microsoft Word conversion failed, trying Pages...")
            success = DocumentConverter._convert_with_pages(input_path, output_path)

        if not success:
            raise RuntimeError("Document conversion failed: Both Word and Pages failed or are not installed.")

        return output_path

    @staticmethod
    def _convert_with_word(input_path: str, output_path: str) -> bool:
        """使用 AppleScript 调用 Microsoft Word 进行转换"""
        script = f'''
        set inputFile to POSIX file "{input_path}"
        set outputFile to POSIX file "{output_path}"
        tell application "Microsoft Word"
            try
                activate
                open inputFile
                set theDoc to active document
                save as theDoc file name (outputFile as text) file format format PDF
                close theDoc saving no
                return true
            on error
                return false
            end try
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return "true" in result.stdout
        except Exception as e:
            logger.error(f"Word conversion error: {e}")
            return False

    @staticmethod
    def _convert_with_pages(input_path: str, output_path: str) -> bool:
        """使用 AppleScript 调用 Pages 进行转换"""
        script = f'''
        set inputFile to POSIX file "{input_path}"
        set outputFile to POSIX file "{output_path}"
        tell application "Pages"
            try
                activate
                set theDoc to open inputFile
                delay 1
                export theDoc to outputFile as PDF
                close theDoc saving no
                return true
            on error
                return false
            end try
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return "true" in result.stdout
        except Exception as e:
            logger.error(f"Pages conversion error: {e}")
            return False

if __name__ == "__main__":
    # 简单的本地测试逻辑
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        try:
            pdf = DocumentConverter.docx_to_pdf(test_file)
            print(f"Success: {pdf}")
        except Exception as e:
            print(f"Error: {e}")
