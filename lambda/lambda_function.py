import boto3
import logging
import json
import urllib.parse
import base64
import io
from PIL import Image
import textwrap
import pyheif
import fitz




logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    s3 = boto3.client('s3')

    bedrock = boto3.client('bedrock-runtime')

    bucket_name = ''
    object_key = ''

    if 's3Bucket' in event and 's3Key' in event:
        logger.info("Received event: " + json.dumps(event))
        bucket_name = event['s3Bucket']
        object_key = event['s3Key']
    else:
        logger.info("Received event: " + json.dumps(event, indent=2))

        bucket_name = urllib.parse.unquote_plus(event['Records'][0]['s3']['bucket']['name'], encoding='utf-8')
        object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    image_content = get_image_from_s3(s3,bucket_name, object_key)

    if object_key.endswith('.heic') or object_key.endswith('.heif'):
        image_content = convert_heic_to_jpg(image_content)

    if object_key.endswith('.pdf'):
        image_content = convert_pdf_to_jpg(image_content)

    image_content_base64 = base64.b64encode(image_content).decode('utf-8')

    analysis_result = analyze_image_with_bedrock(bedrock, image_content_base64)

    logger.info("AI解析结果")
    logger.info(analysis_result)

    # 将结果上传到 S3
    upload_result_to_s3(s3, bucket_name, object_key, analysis_result)

    return {
        'statusCode': 200,
        'body': json.dumps(analysis_result)
    }

def upload_result_to_s3(s3, bucket_name, object_key, analysis_result):
    logger.info("上传解析结果到S3 开始" + analysis_result)

    # 构建 JSON 文件名
    result_key = f"{object_key}.json"

    # 检查analysis_result是否已经是字典类型
    if isinstance(analysis_result, dict):
        result_json = json.dumps(analysis_result, ensure_ascii=False)
    else:
        # 如果是字符串，尝试解析为JSON，如果失败则直接使用
        try:
            json.loads(analysis_result)  # 测试是否为有效的JSON字符串
            result_json = analysis_result  # 如果是有效的JSON字符串，直接使用
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效的JSON字符串，则转换为JSON
            result_json = json.dumps(analysis_result, ensure_ascii=False)

    # 上传到 S3
    s3.put_object(
        Bucket=bucket_name,
        Key=result_key,
        Body=result_json,
        ContentType='application/json'
    )

    logger.info("上传解析结果到S3 结束")


def get_image_from_s3(s3,s3bucket, s3key):
    logger.info("从S3获取图片 开始")

    response = s3.get_object(Bucket=s3bucket, Key=s3key)

    logger.info("从S3获取图片 结束")

    return response['Body'].read()


def b64encode(image_content):
    return base64.b64encode(image_content).decode('utf-8')


def analyze_image_with_bedrock(bedrock, image_content_base64):
    logger.info("调用AI模型 开始")

    prompt = textwrap.dedent("""
        画像は領収書を撮影したものです。領収者氏名、領収金額、領収通貨、支払い先、支払い内容を日本語で教えてください。
        領収通貨は ISO 4217 の通貨名とコードで返してください。
        支払い内容は、宿泊費ならば宿泊費、交通費ならば交通費、それ以外は任意とし、”警告”に「この請求書は宿泊費、交通費以外の可能性があります。」と記載してください。
        また、宿泊費の場合でかつ、ミニバー、洗濯、その他個人の嗜好によるサービス利用料金が含まれる場合、”警告”に「清算対象外の費用（{内訳名称を記載}）が含まれている可能性があります。これらは補償対象外になる場合があります。」と記載してください。
        宿泊費で上記以外の場合、”警告”に「なし」と記載してください。
        解析結果の説明はJSONの説明に出力してください。
        回答は下記フォーマットでJSONで回答してください。
            領収者氏名：空野太郎
            領収金額：100
            領収通貨：日本円
            支払い先：〇〇商事
            支払い内容：宿泊費
            説明：説明文
            警告：警告文
        解析できない項目は、「解析できませんでした」と出力してください。
    """)




    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_content_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    })



    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
        contentType='application/json',
        accept='application/json',
        body=request_body
    )

    response_body = json.loads(response.get('body').read())

    logger.info("调用AI模型 结束")

    return response_body['content'][0]['text']

def convert_heic_to_jpg(image_content):
    heif_file =pyheif.read(image_content)

    image = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        'raw',
        heif_file.mode,
        heif_file.stride,
    )

    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()

def convert_pdf_to_jpg(image_content):
    pdf_document = fitz.open(stream=image_content, filetype='pdf')
    page = pdf_document.load_page(0)
    pix = page.get_pixmap(alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes('png')))
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()