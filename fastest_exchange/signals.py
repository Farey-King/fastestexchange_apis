import os

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from fastest_exchange.messaging.notification import Messenger
from fastest_exchange.middleware import get_current_request

from .models import ClientAccount, Comment, Notification, Profile, User

# Ignore list of items to check for within the signal
IGNORE_SIGNAL_LIST = [
    i.strip() for i in (os.environ.get("IGNORE_SIGNAL_LIST", "")).split(",") if i
]


def format_user_email(user: User):
    return f"{user.get_full_name()} <{user.email}>"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_client_account(sender, instance, created, **kwargs):
    if created:
        ClientAccount.objects.create(user=instance)


# @receiver(pre_save, sender=User)
# def save_profile(sender, instance, **kwargs):
#     instance.profile.save()


# @receiver(post_save, sender=Transaction, dispatch_uid="update_account_balance")
# def create_transaction(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)


@receiver(post_save, sender=Comment)
def comment_added(sender, instance: Comment, created, **kwargs):
    id = instance.transaction.id
    comment_creator: User = instance.created_by
    transaction_creator: User = instance.transaction.created_by

    recipient_list = []

    if transaction_creator != comment_creator:
        recipient_list.append(transaction_creator)

    watchers = (
        Comment.objects.filter(transaction_id=id).select_related("created_by").all()
    )
    seen = set()
    creator_emails = [transaction_creator.email, comment_creator.email]
    for x in watchers:
        user: User = x.created_by
        if user.email not in creator_emails and user.pk not in seen:
            recipient_list.append(user)
            seen.add(user.pk)

    Messenger.send_mail(
        f"{comment_creator.get_full_name()} added a comment to this TRANSACTION (#{id})",
        instance.text,
        [format_user_email(u) for u in recipient_list],
    )


def user_login_success(sender, user: User, **kwargs):
    # Ignore if email in the ignore list
    if user.email.lower() in IGNORE_SIGNAL_LIST:
        return

    request = get_current_request()
    ip_address = request.META.get("REMOTE_ADDR")
    ua = request.user_agent_info
    login_time = timezone.now().strftime("%d %b, %Y %H:%M:%S %z")

    Messenger.send_mail(
        "Logged in to Gandaria Tracker",
        f"""
Dear <strong>{user.get_full_name()}</strong>,

<p>A login attempt to <b>Gandaria Tracker</b> was successful with your credentials.</p>
<p> Date: {login_time} </p>
<p>Request IP: {ip_address}</p>
<p>OS: {ua['os']}</p>
<p>Browser: {ua['browser']}</p>
<p>Device: {ua['device']}</p>

<p>If this was not you, please contact the Administrator immediately.</p>
""",
        [format_user_email(user)],
    )


# user_logged_in.connect(user_login_success)
