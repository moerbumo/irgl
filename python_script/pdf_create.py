from fpdf import FPDF
from PIL import Image
import os

def image_to_pdf_with_blank_page(input_image_path, output_pdf_path):
    """
    画像ファイルをPDFに変換し、先頭に空白ページを追加
    
    引数:
        input_image_path (str): 入力画像ファイルのパス
        output_pdf_path (str): 出力PDFファイルのパス
    """
    # PDFオブジェクトを作成
    pdf = FPDF()
    
    # 空白ページを追加（1ページ目）
    pdf.add_page()
    
    # 画像ページを追加（2ページ目）
    pdf.add_page()
    
    # 画像サイズを取得
    with Image.open(input_image_path) as img:
        img_width, img_height = img.size
    
    # PDFページ（A4: 210×297mm）に合う画像サイズを計算
    pdf_width = 210  # A4幅(mm)
    pdf_height = 297  # A4高さ(mm)
    
    # 画像のアスペクト比を維持
    ratio = min(pdf_width/img_width, pdf_height/img_height)
    img_width *= ratio
    img_height *= ratio
    
    # 画像を中央に配置
    x = (pdf_width - img_width) / 2
    y = (pdf_height - img_height) / 2
    
    pdf.image(input_image_path, x=x, y=y, w=img_width)
    
    pdf.output(output_pdf_path)
    print(f"PDFを生成しました: {output_pdf_path} (全2ページ)")

if __name__ == "__main__":
    supported_formats = ['.gif', '.png', '.jpeg', '.jpg']
    
    for filename in os.listdir('.'):
        if any(filename.lower().endswith(ext) for ext in supported_formats):
            pdf_filename = os.path.splitext(filename)[0] + '.pdf'
            
            # 画像をPDFに変換
            try:
                image_to_pdf_with_blank_page(filename, pdf_filename)
            except Exception as e:
                print(f"ファイル {filename} の処理中にエラーが発生しました: {str(e)}")
