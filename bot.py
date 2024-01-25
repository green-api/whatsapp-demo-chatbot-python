from yaml import safe_load
from user_manager import Manager
from re import IGNORECASE
from whatsapp_chatbot_python import (
    BaseStates,
    GreenAPIBot,
    Notification,
    filters,
)


# These parameters are available in the personal cabinet
# https://console.green-api.com/, copy and paste them in the corresponding
# fields

# Do not get rid of quotation marks

# Example of filling personal data:

# ID_INSTANCE = '1101123456'
# API_TOKEN_INSTANCE= 'abcdefghjklmn1234567890oprstuwxyz'

ID_INSTANCE = ''
API_TOKEN_INSTANCE = ''

bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE
)

with open('data.yml', 'r', encoding='utf8') as stream:
    data = safe_load(stream)


class States(BaseStates):
    ACTIVE = 'active'
    LANGUAGE_SET = 'lang_set'


manager = Manager()


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=None)
def message_handler(notification: Notification) -> None:
    notification.state_manager.update_state(notification.sender,
                                            States.ACTIVE.value)
    user = manager.check_user(notification.chat)
    notification.answer(data['select_language'])


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['1', '/1', '1.', '1 '])
def set_eng(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('eng')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['2', '/2', '2.', '2 '])
def set_ru(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('ru')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['3', '/3', '3.', '3 '])
def set_he(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('he')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['4', '/4', '4.', '4 '])
def set_es(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('es')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['5', '/5', '5.', '5 '])
def set_ar(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('ar')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['1', '/1', '1.', '1 '])
def option_1(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_text_message"][user.language]}'
        f'{data["links"][user.language]["send_text_documentation"]}'
        )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['2', '/2', '2.', '2 '])
def option_2(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile='https://images.rawpixel.com/image_png_1100/cHJpdmF0ZS9'
                'sci9pbWFnZXMvd2Vic2l0ZS8yMDIzLTExL3Jhd3BpeGVsb2ZmaWNlM'
                'TlfcGhvdG9fb2ZfY29yZ2lzX2luX2NocmlzdG1hc19zd2VhdGVyX2l'
                'uX2FfcGFydF80YWM1ODk3Zi1mZDMwLTRhYTItYWM5NS05YjY3Yjg1M'
                'TFjZmUucG5n.png',
        fileName='corgi.png',
        caption=f'{data["send_file_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
        )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['3', '/3', '3.', '3 '])
def option_3(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile='https://images.rawpixel.com/image_1100/cHJpdmF0ZS9sci9'
                'pbWFnZXMvd2Vic2l0ZS8yMDIzLTExL3Jhd3BpeGVsX29mZmljZV8zM'
                'F9hX3Bob3RvX29mX2hhcHB5X2NvcmdpX2RvZ193ZWFyaW5nX3NhbnR'
                'hX3N1aV8yNjIxNjEzNi0wNTA5LTQ0ZDMtOTA2NS00MDZlODNhOTBmO'
                'TBfMi5qcGc.jpg',
        fileName='corgi.jpg',
        caption=f'{data["send_image_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['4', '/4', '4.', '4 '])
def option_4(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        # TODO: get file links
        urlFile="TODO",
        fileName='green-api.mp3',
        caption=f'{data["send_audio_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['5', '/5', '5.', '5 '])
def option_5(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        # TODO: get file links
        urlFile="TODO",
        fileName='green-api.mp4',
        caption=f'{data["send_video_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['6', '/6', '6.', '6 '])
def option_6(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_contact_message"][user.language]}'
        f'{data["links"][user.language]["send_contact_documentation"]}'
    )
    notification.api.sending.sendContact(
        chatId=notification.chat,
        contact={
            'phoneContact': notification.chat.split('@')[0],
            'firstName': notification.event['senderData']['senderName'],
        },
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['7', '/7', '7.', '7 '])
def option_7(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_location_message"][user.language]}'
        f'{data["links"][user.language]["send_location_documentation"]}'
    )
    notification.api.sending.sendLocation(
        chatId=notification.chat,
        latitude=35.888171,
        longitude=14.440230,
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['8', '/8', '8.', '8 '])
def option_8(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_poll_message"][user.language]}'
        f'{data["links"][user.language]["send_poll_documentation"]}'
    )
    notification.api.sending.sendPoll(
        chatId=notification.chat,
        message=f'{data["poll_question"][user.language]}',
        options=[
            {"optionName": f'{data["poll_option_1"][user.language]}'},
            {"optionName": f'{data["poll_option_2"][user.language]}'},
            {"optionName": f'{data["poll_option_3"][user.language]}'}
        ],
        multipleAnswers=False
    )

@bot.router.polls()
def polls_handler(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    vote_data = notification.event["messageData"]["pollMessageData"]["votes"]
    sender_vote = None

    for vote in vote_data:
        if notification.event["senderData"]["sender"] in vote["optionVoters"]:
            sender_vote = vote["optionName"]
            break
    if sender_vote == "Yes":
        notification.api.sending.sendMessage(notification.chat, f'{data["poll_answer_1"][user.language]}')
    if sender_vote == "No":
        notification.api.sending.sendMessage(notification.chat, f'{data["poll_answer_2"][user.language]}')
    else :
        notification.api.sending.sendMessage(notification.chat, f'{data["poll_answer_3"][user.language]}')

@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['9', '/9', '9.', '9 '])
def option_9(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["get_avatar_message"][user.language]}'
        f'{data["links"][user.language]["get_avatar_documentation"]}'
    )
    response = notification.api.serviceMethods.getAvatar(notification.chat)
    if response.data["urlAvatar"]:
        notification.api.sending.sendMessage(notification.chat, f'{data["avatar_found"][user.language]}')
        notification.api.sending.sendFileByUrl(notification.chat, response.data["urlAvatar"], "your_avatar.png")
    else:
        notification.api.sending.sendMessage(notification.chat, f'{data["avatar_not_found"][user.language]}')
    
@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['10', '/10', '10.', '10 '])
def option_10(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendMessage(
        notification.chat,
        f'{data["send_link_message_preview"][user.language]}'
        f'{data["links"][user.language]["send_link_documentation"]}',
        linkPreview=True
    )
    notification.api.sending.sendMessage(
        notification.chat,
        f'{data["send_link_message_no_preview"][user.language]}',
        linkPreview=False
    )

@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['11', '/11', '11.', '11 '])
def option_11(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    group_response = notification.api.groups.createGroup(
        f'{data["group_name"][user.language]}',
        [notification.chat, bot.api.account.getSettings().data["wid"]]
    )
    if group_response.data["created"]:
        group_picture_response = notification.api.groups.setGroupPicture(
            f'{group_response.data["chatId"]}',
            ('file',('{{file}}.jpeg',open('C:/{{file}}.jpeg','rb'),'image/jpeg'))
        )
        if group_picture_response.data["setGroupPicture"]:
            notification.api.sending.sendMessage(
                f'{group_response.data["chatId"]}',
                f'{data["send_group_message"][user.language]}'
                f'{data["links"][user.language]["groups_documentation"]}',
            )
        else:
            notification.api.sending.sendMessage(
                f'{group_response.data["chatId"]}',
                f'{data["send_group_message_set_picture_false"][user.language]}'
                f'{data["links"][user.language]["groups_documentation"]}',
            )

@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['12', '/12', '12.', '12 '])
def option_12(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendMessage(
        notification.chat,
        f'{data["send_quoted_message"][user.language]}'
        f'{data["links"][user.language]["send_quoted_message_documentation"]}',
        quotedMessageId=notification.event["idMessage"]
    )

@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['stop', 'стоп', 'Stop', 'Стоп'])
def stop(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.state_manager.update_state(notification.chat, None)
    notification.answer(
        f'{data["stop_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'!'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['menu', 'меню', 'Menu', 'Меню'])
def menu(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(data['menu'][user.language])


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    regexp=(r'^((?!1|2).)*$', IGNORECASE))
def not_recognized_message1(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: message_handler(Notification)
    notification.answer(data['specify_language'])


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    regexp=(r'^((?![1-5]|menu|меню|stop|стоп|'
                            r'Menu|Меню|Stop|Стоп).)*$',
                            IGNORECASE))
def not_recognized_message2(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: message_handler(Notification)
    notification.answer(data['not_recognized_message'][user.language])


bot.run_forever()