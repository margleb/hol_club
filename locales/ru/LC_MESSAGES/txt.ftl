start-hello =
    Привет, { $username }!

    Добро пожаловать в Клуб холостяков ✨

    Если ты здесь — значит, открыт(а) к знакомствам, общению

    Этот бот поможет тебе:

    • записываться на мероприятия клуба
    • следить за своими регистрациями
    • быть ближе к людям с похожими целями

    📢 Наш основной канал — @hol_club

    Готов(а) начать? Тогда выбирай действие 👇
start-events-title = Ваши мероприятия
start-events-list-button = Мои регистрации
start-events-empty = У вас пока нет записей на мероприятия.
start-events-item = { $name } — { $datetime }{ $tags }
start-events-page = Страница { $current } из { $total }
start-events-prev-button = ◀️
start-events-next-button = ▶️
start-admin-registrations-button = Список регистраций
start-admin-partners-button = Партнеры
start-admin-partner-commissions-button = Комиссия партнеров
start-admin-partner-commissions-title = Комиссия партнеров
start-admin-partner-commissions-empty = Партнеров пока нет.
start-admin-partner-commissions-item = { $username } • { $percent }%
start-admin-partner-commission-edit-prompt =
    Партнер: { $username }
    Текущая комиссия: { $percent }%

    Введите новый процент комиссии (0-100):
start-admin-partner-commission-edit-invalid = Не удалось определить партнера для изменения комиссии.
start-admin-partner-commission-invalid = Некорректный процент. Введите число от 0 до 100.
start-admin-partner-commission-updated = Комиссия обновлена: { $percent }%.
start-admin-partner-requests-title = Заявки на партнерство
start-admin-partner-requests-empty = Заявок на партнерство нет.
start-admin-partner-requests-item = { $username } (id:{ $user_id })
start-admin-partner-request-details =
    Пользователь: { $username }
    ID: { $user_id }
start-admin-registrations-partners-title = Партнеры
start-admin-registrations-partners-empty = Партнеров пока нет.
start-admin-registrations-partners-item = { $username } • { $percent }% • { $pending }
start-admin-partner-actions-title = Партнер: { $username }
start-admin-partner-actions-invalid = Не удалось определить партнера.
start-admin-partner-actions-commission-button = Установить комиссию
start-admin-partner-actions-registrations-button = Список регистраций
start-admin-registrations-pending-title = Ожидают подтверждения оплаты ({ $partner })
start-admin-registrations-pending-empty = По выбранному партнеру нет ожидающих подтверждения оплат.
start-admin-registrations-pending-item = { $username } • { $event_name } • { $amount } ₽
start-admin-registrations-pending-contact-button = Написать
start-admin-registrations-pending-message-prompt = Напишите сообщение пользователю { $username }.
start-admin-registrations-pending-message-invalid = Не удалось отправить сообщение пользователю.
start-admin-registrations-pending-message-sent = Сообщение отправлено пользователю.
start-admin-registrations-pending-message-sender-admin = администратора
start-admin-registrations-pending-message-sender-partner = организатора
start-admin-registrations-pending-message-to-user =
    Сообщение от { $sender_role } { $sender }:
    { $text }
start-admin-registrations-pending-reply-button = Ответить
start-admin-registrations-pending-reply-back-button = Ответить
start-admin-registrations-pending-reply-prompt = Напишите ответ администратору.
start-admin-registrations-pending-reply-sent = Сообщение отправлено администратору.
start-admin-registrations-pending-reply-failed = Не удалось отправить сообщение администратору.
start-admin-registrations-pending-reply-admin-received =
    Ответ от пользователя { $username }:
    { $text }
start-admin-registrations-pending-write-button = Написать
start-user-event-message-partner-to-partner =
    Сообщение от участника { $username } по мероприятию «{ $event_name }»:
    { $text }
start-event-past-tag = [уже прошло]
partner-events-title = Ваши события
partner-events-list-button = Мои события
partner-events-empty = У вас пока нет созданных мероприятий.
partner-events-item = { $name } — { $datetime }
partner-events-page = Страница { $current } из { $total }
partner-events-prev-button = ◀️
partner-events-next-button = ▶️
start-event-details-text = { $name }
    { $datetime }{ $tags }
start-event-details-missing = Не удалось найти мероприятие.
start-event-view-topic-button = Смотреть топик

stranger = Странник

help-command = Доступные команды:

               <b>Общие команды:</b>

               /start - Перезапустить бота
               /help - Посмотреть эту справку

               <b>Партнерство:</b>

               /partner_request - Отправить заявку на партнерство

about-author = Об авторе

about-author-link = https://t.me/toBeAnMLspecialist/935

free-course = 🤖 Бесплатный курс по ботам

free-course-link = https://stepik.org/course/120924

advanced-course = 🚀 Продвинутый курс по ботам

advanced-course-link = https://stepik.org/a/153850

mlpodcast = Machine Learning Podcast

mlpodcast-link = https://mlpodcast.mave.digital/

back-button = ◀️ Назад

save-button = ✅ Сохранить

set-lang-menu = <b>Пожалуйста, выберите язык интерфейса бота</b>

                Выбран 🇷🇺 <b>Русский язык</b>

ru-lang = 🇷🇺 Русский

en-lang = 🇬🇧 Английский

fr-lang = 🇫🇷 Французский

de-lang = 🇩🇪 Немецкий

lang-saved = ✅ Настройки языка успешно сохранены!

partner-request-forbidden = У вас уже есть права партнера или администратора.

partner-request-sent = Заявка на партнерство отправлена. Администратор рассмотрит ее.

partner-request-pending = Ваша заявка уже на рассмотрении.

partner-request-approved = Ваша заявка уже одобрена. Роль партнера активирована.

partner-approve-forbidden = Недостаточно прав для одобрения заявок.


partner-approve-missing = Заявка на партнерство не найдена.

partner-approve-already = Эта заявка уже одобрена.

partner-approve-user-missing = Пользователь не найден.

partner-approve-success = Заявка одобрена. Пользователь { $user_id } теперь партнер.

partner-request-button = Заявка на партнерство

partner-request-channel-text = Хочешь стать партнером? Нажми кнопку ниже.

partner-request-channel-posted = Сообщение с заявкой опубликовано в канале.

partner-request-channel-failed = Не удалось отправить сообщение в канал.

partner-request-admin-notify = Заявка на партнерство от { $username } (id: { $user_id }).
partner-request-list-header = Заявки на партнерство: { $count }.
partner-request-list-empty = Заявок на партнерство нет.
partner-request-list-item = Пользователь { $user_id } хочет стать партнером.
partner-request-list-button = Список заявок
partner-request-contact-button = Связаться

partner-request-approve-button = Принять

partner-request-reject-button = Отклонить

partner-request-rejected = Ваша заявка на партнерство отклонена.

partner-request-already-rejected = Эта заявка уже отклонена.

partner-request-invalid = Некорректные данные заявки.

partner-decision-approved = Заявка одобрена.

partner-decision-rejected = Заявка отклонена.

partner-request-channel-missing = Не указан канал для заявок. Добавьте EVENTS_CHANNEL в .env.

partner-event-create-button = Создать событие

partner-event-forbidden = У вас нет прав для создания событий.

partner-event-name-prompt = Введите название события (от <b>{ $min }</b> до <b>{ $max }</b> символов).

partner-event-name-invalid = Название должно быть от <b>{ $min }</b> до <b>{ $max }</b> символов.

partner-event-image-prompt = Пришлите изображение события или пропустите этот шаг.

partner-event-skip-button = Пропустить

partner-event-datetime-prompt = Введите дату и время (например <b>2026.01.01 00:00</b>).

partner-event-datetime-invalid = Некорректный формат даты и времени. Пример: <b>2026.01.01 00:00</b>.

partner-event-datetime-past = Дата должна быть в будущем. Пример: <b>2026.01.01 00:00</b>.

partner-event-address-prompt = Введите адрес в <b>г. Москва</b> с точным указанием до номера дома.
partner-event-address-empty = Не удалось найти адреса. Попробуйте уточнить запрос.

partner-event-address-select-prompt = Выберите адрес из подсказок.

partner-event-address-invalid = Некорректный выбор адреса. Попробуйте снова.

partner-event-address-house-missing = Укажите номер дома в адресе.
partner-event-address-city-moscow = Адрес должен быть в <b>г. Москва</b>.

partner-event-description-prompt = Введите описание (от <b>{ $min }</b> до <b>{ $max }</b> символов).

partner-event-description-invalid = Описание должно быть от <b>{ $min }</b> до <b>{ $max }</b> символов.

partner-event-participation-prompt = Выберите тип участия.

partner-event-participation-free = Бесплатно

partner-event-participation-paid = Платно

partner-event-price-prompt = Введите базовую стоимость (до <b>{ $max }</b> ₽). Комиссия <b>{ $commission_percent }%</b> будет добавлена автоматически.

partner-event-price-invalid = Некорректная стоимость. Максимум <b>{ $max }</b> ₽.

partner-event-ticket-link-prompt = Введите ссылку на билет (Adv.Cake). Это обязательный шаг для администратора.

partner-event-ticket-link-invalid = Некорректная ссылка. Укажите полный URL, например https://go.2038.pro/...

partner-event-ticket-link-preview = Ссылка на билет: { $url }

partner-event-ticket-link-text =
    Чтобы получить доступ к чату мероприятия «{ $event_name }», купите билет по ссылке ниже.
    После подтверждения оплаты ссылка придёт автоматически.

partner-event-ticket-link-waiting = Оплата ещё не подтверждена. Обычно это занимает до 10 минут.

partner-event-ticket-link-missing = Для этого события не указана ссылка на билет.

partner-event-prepay-percent-prompt = Введите процент предоплаты (от <b>0</b> до <b>100</b>%).

partner-event-prepay-percent-invalid = Некорректный процент. Введите число от <b>0</b> до <b>100</b>.

partner-event-prepay-free-prompt = Введите сумму предоплаты (до <b>{ $max }</b> ₽). Для бесплатного мероприятия сумма возвращается после посещения.

partner-event-prepay-free-invalid = Некорректная сумма. Максимум <b>{ $max }</b> ₽.

partner-event-age-prompt = Выберите возрастную группу или «Любой».

partner-event-age-invalid = Некорректная возрастная группа. Выберите вариант из списка.

partner-event-age-everyone = Любой

partner-event-chat-male-prompt = Введите ссылку на мужской чат.
partner-event-chat-female-prompt = Введите ссылку на женский чат.
partner-event-chat-male-invalid = Некорректная ссылка на мужской чат.
partner-event-chat-female-invalid = Некорректная ссылка на женский чат.


partner-event-preview-title = Превью события:

partner-event-preview-photo-attached = Фото будет прикреплено.

partner-event-preview-trimmed = Текст был сокращен из-за лимита подписи.

partner-event-chat-male-preview = Мужской чат: { $url }
partner-event-chat-female-preview = Женский чат: { $url }

partner-event-publish-button = Опубликовать

partner-event-edit-name-button = Редактировать название

partner-event-edit-image-button = Редактировать изображение

partner-event-edit-datetime-button = Редактировать дату и время

partner-event-edit-address-button = Редактировать адрес

partner-event-edit-description-button = Редактировать описание

partner-event-edit-participation-button = Редактировать тип участия

partner-event-edit-price-button = Редактировать стоимость

partner-event-edit-ticket-link-button = Редактировать ссылку на билет

partner-event-edit-prepay-button = Редактировать предоплату

partner-event-edit-age-button = Редактировать возраст

partner-event-chat-male-edit-button = Редактировать мужской чат
partner-event-chat-female-edit-button = Редактировать женский чат


partner-event-join-chat-button = Зарегистрироваться
partner-event-buy-ticket-button = Купить билет
partner-event-join-chat-link-button = Перейти в чат
partner-event-join-chat-text = Вот ссылка на чат мероприятия «{ $event_name }»:
partner-event-join-chat-missing = Не удалось найти чат для этого события.
partner-event-join-chat-self-forbidden = Вы не можете регистрироваться на своё мероприятие.
partner-event-join-chat-role-forbidden = Партнёры и администраторы не могут регистрироваться на мероприятия.
partner-event-join-chat-hint = Пол и возраст можно изменить в личном кабинете.
partner-event-prepay-text = Для регистрации нужна предоплата — это гарантирует, что участники действительно придут.

                Сумма предоплаты: { $amount } ₽
                Номер карты: { $card_number }
                После подтверждения оплаты вы получите ссылку на приватный чат мероприятия.

                { $refund_note }

partner-event-prepay-free-refund = Для бесплатного мероприятия предоплата возвращается после посещения.
partner-event-prepay-paid-button = Я оплатил
partner-event-prepay-confirm-prompt = Вы подтверждаете, что внесли предоплату?
partner-event-prepay-confirm-yes = Да
partner-event-prepay-confirm-no = Нет
partner-event-prepay-receipt-prompt = Отправьте чек об оплате (фото или документ).
partner-event-prepay-receipt-invalid = Пожалуйста, отправьте чек в формате фото или документа.
partner-event-prepay-receipt-required = Для подтверждения оплаты нужен отправленный чек.
partner-event-prepay-sent = Спасибо! Ожидаем подтверждение оплаты от администратора.
partner-event-prepay-contact-button = Уточнить статус оплаты
partner-event-prepay-contact-partner-button = Написать организатору
partner-event-prepay-contact-partner-prompt = Напишите сообщение организатору.
partner-event-prepay-contact-partner-sent = Сообщение отправлено организатору.
partner-event-prepay-contact-partner-failed = Не удалось отправить сообщение организатору.
partner-event-prepay-cancelled = Хорошо, подтвердите оплату, когда будете готовы.
partner-event-prepay-waiting = Оплата уже ожидает подтверждения администратора.
partner-event-prepay-notify =
    Требуется подтверждение оплаты мероприятия.
    Мероприятие: «{ $event_name }»
    Партнер: { $partner_username }
    Сумма к оплате: { $amount } ₽
    Пользователь: { $username }
partner-event-prepay-approved = Ваша предоплата подтверждена. Вы зарегистрированы на мероприятие.
partner-event-prepay-approved-partner = Предоплата подтверждена.
partner-event-prepay-approved-partner-notify = Пользователь { $username } зарегистрирован на мероприятие «{ $event_name }».
partner-event-ticket-approved = Покупка билета подтверждена. Вы зарегистрированы на мероприятие.
partner-event-ticket-approved-partner-notify = Пользователь { $username } купил билет на мероприятие «{ $event_name }».
partner-event-prepay-declined = Оплата отклонена администратором. Если есть вопросы — напишите в поддержку.
partner-event-prepay-declined-partner = Оплата отклонена.
partner-event-prepay-already-processed = Эта оплата уже обработана.
partner-event-prepay-admin-only = Подтверждать или отклонять оплату может только администратор.
partner-event-prepay-admin-missing = Сейчас нет администраторов для подтверждения оплаты. Напишите в поддержку.

partner-event-registrations-pending-button = Ожидают подтверждения
partner-event-registrations-confirmed-button = Зарегистрированные
partner-event-registrations-pending-title = Ожидают подтверждения оплаты
partner-event-registrations-pending-empty = Пока нет ожидающих подтверждения.
partner-event-registrations-pending-item = { $username } • { $amount } ₽
partner-event-registrations-pending-details-missing = Не удалось найти заявку.
partner-event-registrations-pending-details-text =
    Пользователь: { $username }
    Стоимость: { $amount } ₽
partner-event-registrations-pending-approve-button = Подтвердить
partner-event-registrations-pending-decline-button = Отклонить
partner-event-registrations-confirmed-title = Зарегистрированные пользователи
partner-event-registrations-confirmed-empty = Пока нет подтвержденных регистраций.
partner-event-registrations-confirmed-item = { $username }
partner-event-view-post-button = Смотреть пост
partner-event-view-topic-button = Смотреть топик
partner-event-view-chat-button = Смотреть чат

partner-event-publish-success = Событие опубликовано.

partner-event-publish-failed = Не удалось опубликовать событие.

partner-event-publish-already = Событие уже опубликовано.

partner-event-publish-in-progress = Публикация уже выполняется.

partner-event-channel-missing = Не указан канал для событий. Добавьте EVENTS_CHANNEL в .env.
partner-event-private-chat-missing = Не настроен Telethon. Добавьте TELETHON_API_ID, TELETHON_API_HASH и TELETHON_SESSION в .env.
partner-event-private-chat-create-failed = Не удалось создать приватный чат события через Telethon. Проверьте сессию и права аккаунта.


partner-event-label-datetime = <b>Дата и время:</b> { $value }

partner-event-label-address = <b>Адрес:</b> { $value }

partner-event-label-participation = <b>Участие:</b> { $value } ₽

partner-event-label-age = <b>Возраст:</b> { $value }

partner-event-text-template =

    <b>{ $name }</b>
    ────────────

    { $datetime }
    { $address }
    { $participation }
    { $age_block }

    { $description_block }

general-registration-gender-prompt = Укажите ваш пол
general-registration-gender-male = Мужчина
general-registration-gender-female = Женщина
general-registration-age-prompt = Сколько вам лет?
general-registration-age-group = { $range } лет
general-registration-thanks = Спасибо за регистрацию!
general-registration-subscribe =
    Подпишитесь на канал { $channel } и чат.
general-registration-under35 = Чат для тех, кому меньше 35 лет.
general-registration-channel-button = Канал @hol_club
general-registration-chat-male-button = Чат для мужчин
general-registration-chat-female-button = Чат для женщин
general-registration-under35-button = Чат до 35 лет
general-registration-already = Вы уже зарегистрированы.
general-registration-links-missing = Не удалось получить ссылки для регистрации. Сообщите администратору.
general-registration-request-text =
    Пожалуйста, укажите ваш пол и возрастную группу, чтобы мы могли корректно подбирать чаты и уведомления.
general-registration-request-button = Заполнить анкету
general-registration-request-empty = Нет пользователей для рассылки.
profile-nudge-first-text =
    Привет! Вы начали анкету в боте, но не завершили ее.

    Это займет 1-2 минуты. После заполнения открою доступ к чатам и каналу.
profile-nudge-reminder-text =
    Небольшое напоминание: анкета все еще не завершена.

    Как только заполните ее, сразу пришлю доступ к чатам и каналу.
profile-nudge-button = Продолжить анкету

account-button = Мой аккаунт
account-intro-text = Привет 👋
                
                Это Клуб холостяков — сообщество одиноких людей в Москве, которые хотят знакомиться оффлайн.

                Я задам пару коротких вопросов — это займёт меньше минуты.

account-intro-button = Поехали
account-gender-prompt = Выберите ваш пол
account-age-prompt = Выберите возрастную группу
account-intent-prompt = Если в клубе холостяков будет проходить встреча, то когда вы будете готовы ее посетить?
account-intent-hot = ✅ В ближайшие 7 дней
account-intent-warm = 🟡 В течение месяца
account-intent-cold = 🧊 Пока не готов(а)
account-final-text = Готово 👍

                Подпишись на { $channel } и { $chat }.

                Я буду звать тебя только на подходящие форматы и не буду спамить.

account-final-channel-button = Канал клуба
account-final-chat-male-button = Мужской чат
account-final-chat-female-button = Женский чат
account-final-channel = канал клуба
account-final-chat-male = мужской чат
account-final-chat-female = женский чат
account-summary-title = Проверьте ваши ответы
account-summary-age = Возраст
account-summary-gender = Пол
account-summary-intent = Готовность
account-summary-edit-age-button = Изменить возраст
account-summary-edit-gender-button = Изменить пол
account-summary-edit-intent-button = Изменить готовность
account-summary-confirm-button = Всё верно
account-summary-close-button = Готово
account-updated = Профиль обновлен.
