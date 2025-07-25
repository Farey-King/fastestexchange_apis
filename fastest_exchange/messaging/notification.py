import threading

from django.core.mail import EmailMessage, send_mail


class EmailThread(threading.Thread):
    def __init__(self, subject: str, html_content: str, recipient_list: list[str]):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        threading.Thread.__init__(self)

    def run(self):
        try:
            msg = EmailMessage(
                subject=self.subject, body=self.html_content, to=self.recipient_list
            )
            msg.content_subtype = "html"
            msg.send()
        except Exception as e:
            print("Error sending E-mail!")
            print(e)


class Messenger:

    @staticmethod
    def send_mail(subject: str, html_content: str, recipient_list: list[str]):
        EmailThread(subject, html_content, recipient_list).start()
