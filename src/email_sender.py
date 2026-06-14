import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header


def attach_file(msg, file_path):
    # 파일 경로가 없으면 첨부하지 않음
    if not file_path:
        return

    # 실제 파일이 존재하지 않으면 첨부하지 않음
    if not os.path.exists(file_path):
        return

    # 첨부할 파일을 바이너리 형식으로 읽기
    with open(file_path, "rb") as f:
        part = MIMEApplication(f.read())

    filename = os.path.basename(file_path)

    # 이메일 첨부파일 정보 추가
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=filename
    )

    msg.attach(part)


def send_email_with_files(
    sender_email,
    sender_password,
    receiver_email,
    subject,
    body,
    file_paths=None
):
    # 첨부파일 목록이 없으면 빈 리스트로 설정
    if file_paths is None:
        file_paths = []

    # 이메일 메시지 객체 생성
    msg = MIMEMultipart()
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # 이메일 본문 추가
    text_part = MIMEText(body, _subtype="plain", _charset="utf-8")
    msg.attach(text_part)

    # 결과 파일들을 이메일에 첨부
    for file_path in file_paths:
        attach_file(msg, file_path)

    # 네이버 SMTP 서버에 연결
    smtp = smtplib.SMTP("smtp.naver.com", 587)
    smtp.ehlo()
    smtp.starttls()

    # 로그인 후 이메일 전송
    smtp.login(sender_email, sender_password)
    smtp.sendmail(sender_email, receiver_email, msg.as_string())
    smtp.quit()

    return True