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
start-admin-registrations-pending-title = Ожидают подтверждения оплаты
start-admin-registrations-pending-empty = Нет ожидающих подтверждения оплат.
start-admin-registrations-pending-item = { $username } • { $event_name } • { $amount } ₽
start-admin-events-button = Предстоящие события
start-admin-events-title = Предстоящие события
start-admin-events-empty = Вы ещё не создали мероприятий.
start-admin-events-item = { $name } — { $datetime }
start-admin-events-button = Предстоящие события
start-admin-events-title = Предстоящие события
start-admin-events-empty = Вы ещё не создали мероприятий.
start-admin-events-item = { $name } — { $datetime }
start-event-past-tag = [уже прошло]
start-event-details-text = { $name }
    { $datetime }{ $tags }
start-event-details-missing = Не удалось найти мероприятие.
start-event-view-topic-button = Смотреть топик

stranger = Странник

help-command = Доступные команды:

               <b>Общие команды:</b>

               /start - Перезапустить бота
               /help - Посмотреть эту справку

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

partner-event-price-prompt = Введите стоимость (до <b>{ $max }</b> ₽).

partner-event-price-invalid = Некорректная стоимость. Максимум <b>{ $max }</b> ₽.

partner-event-commission-prompt = Введите комиссию администратора в процентах (от <b>0</b> до <b>100</b>%).

partner-event-commission-invalid = Некорректная комиссия. Введите число от <b>0</b> до <b>100</b>.

partner-event-ticket-link-prompt = Введите ссылку на билет (Adv.Cake). Это обязательный шаг для администратора.

partner-event-ticket-link-invalid = Некорректная ссылка. Укажите полный URL, например https://go.2038.pro/...

partner-event-ticket-link-preview = Ссылка на билет: { $url }

partner-event-ticket-link-text =
    Чтобы получить доступ к чату мероприятия «{ $event_name }», купите билет по ссылке ниже.
    После подтверждения оплаты ссылка придёт автоматически.

partner-event-ticket-link-waiting = Оплата ещё не подтверждена. Обычно это занимает до 10 минут.

partner-event-ticket-link-missing = Для этого события не указана ссылка на билет.

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
partner-event-publish-target-prompt = Выберите, где опубликовать событие.
partner-event-publish-target-bot = В боте
partner-event-publish-target-channel = В канале
partner-event-publish-target-both = В боте и канале
partner-event-publish-target-selected = ✓
partner-event-publish-target-invalid = Некорректный вариант публикации. Выберите вариант из списка.

partner-event-edit-name-button = Редактировать название

partner-event-edit-image-button = Редактировать изображение

partner-event-edit-datetime-button = Редактировать дату и время

partner-event-edit-address-button = Редактировать адрес

partner-event-edit-description-button = Редактировать описание

partner-event-edit-price-button = Редактировать стоимость

partner-event-edit-commission-button = Редактировать комиссию

partner-event-edit-ticket-link-button = Редактировать ссылку на билет

partner-event-edit-age-button = Редактировать возраст

partner-event-chat-male-edit-button = Редактировать мужской чат
partner-event-chat-female-edit-button = Редактировать женский чат


partner-event-join-chat-button = Зарегистрироваться
partner-event-buy-ticket-button = Купить билет
partner-event-join-chat-link-button = Перейти в чат
partner-event-join-chat-text = Вот ссылка на чат мероприятия «{ $event_name }»:
partner-event-join-chat-missing = Не удалось найти чат для этого события.
partner-event-join-chat-self-forbidden = Вы не можете регистрироваться на своё мероприятие.
partner-event-join-chat-role-forbidden = Администраторы не могут регистрироваться на мероприятия.
partner-event-join-chat-hint = Если не удается открыть чат, напишите администратору.
partner-event-prepay-text = Для регистрации нужно оплатить участие.

                Сумма оплаты: { $amount } ₽
                Номер карты: { $card_number }
                После подтверждения оплаты вы получите ссылку на приватный чат мероприятия.
partner-event-prepay-paid-button = Я оплатил
partner-event-prepay-confirm-prompt = Вы подтверждаете, что оплатили участие?
partner-event-prepay-confirm-yes = Да
partner-event-prepay-confirm-no = Нет
partner-event-prepay-receipt-prompt = Отправьте чек об оплате (фото или документ).
partner-event-prepay-receipt-invalid = Пожалуйста, отправьте чек в формате фото или документа.
partner-event-prepay-receipt-required = Для подтверждения оплаты нужен отправленный чек.
partner-event-prepay-sent = Спасибо! Ожидаем подтверждение оплаты от организатора.
partner-event-prepay-contact-button = Уточнить статус оплаты
partner-event-prepay-contact-partner-button = Написать организатору
partner-event-prepay-contact-partner-prompt = Напишите сообщение организатору.
partner-event-prepay-contact-partner-sent = Сообщение отправлено организатору.
partner-event-prepay-contact-partner-failed = Не удалось отправить сообщение организатору.
partner-event-dialog-organizer-button = Написать организатору
partner-event-dialog-participant-button = Написать участнику
partner-event-dialog-open-button = Ответить
partner-event-dialog-prompt-organizer = Отправьте текстовое сообщение организатору.
partner-event-dialog-prompt-participant = Отправьте текстовое сообщение участнику.
partner-event-dialog-text-only = Сейчас можно отправлять только текстовые сообщения.
partner-event-dialog-validation-empty = Сообщение не должно быть пустым.
partner-event-dialog-send-failed = Не удалось доставить сообщение. Попробуйте позже.
partner-event-dialog-sent = Сообщение отправлено.
partner-event-dialog-inaccessible = Диалог недоступен.
partner-event-dialog-compose-organizer = <b>Сообщение организатору</b>
    Мероприятие: «{ $event_name }»
partner-event-dialog-compose-participant = <b>Сообщение участнику</b>
    Участник: { $participant }
    Мероприятие: «{ $event_name }»
partner-event-dialog-notification-organizer =
    <b>От организатора:</b> { $sender }
    <b>Мероприятие:</b> «{ $event_name }»
    { $text }
partner-event-dialog-notification-participant =
    <b>От участника:</b> { $sender }
    <b>Мероприятие:</b> «{ $event_name }»
    { $text }
partner-event-prepay-cancelled = Хорошо, подтвердите оплату, когда будете готовы.
partner-event-prepay-waiting = Оплата уже ожидает подтверждения организатора.
partner-event-prepay-notify =
    Требуется подтверждение оплаты мероприятия.
    Мероприятие: «{ $event_name }»
    Организатор: { $organizer_username }
    Сумма к оплате: { $amount } ₽
    Пользователь: { $username }
partner-event-prepay-approved = Ваша оплата подтверждена. Вы зарегистрированы на мероприятие.
partner-event-prepay-approved-partner = Оплата подтверждена.
partner-event-prepay-approved-partner-notify = Пользователь { $username } зарегистрирован на мероприятие «{ $event_name }».
partner-event-ticket-approved = Покупка билета подтверждена. Вы зарегистрированы на мероприятие.
partner-event-ticket-approved-partner-notify = Пользователь { $username } купил билет на мероприятие «{ $event_name }».
partner-event-prepay-declined = Оплата отклонена организатором. Если есть вопросы — напишите в поддержку.
partner-event-prepay-declined-partner = Оплата отклонена.
partner-event-prepay-already-processed = Эта оплата уже обработана.
partner-event-prepay-admin-only = Подтверждать или отклонять оплату может только организатор мероприятия.
partner-event-prepay-admin-missing = Не удалось доставить чек организатору мероприятия. Попробуйте позже или свяжитесь с поддержкой.

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
partner-event-registrations-confirmed-details-missing = Не удалось найти участника.
partner-event-registrations-confirmed-details-text =
    Пользователь: { $username }
    Мероприятие: { $event_name }
    Стоимость: { $amount } ₽
    Статус: { $status }
partner-event-registrations-confirmed-status-confirmed = Оплата подтверждена
partner-event-registrations-confirmed-status-attended = Участие подтверждено
partner-event-reminder-text =
    Напоминаем, что вы зарегистрированы на мероприятие «{ $event_name }».
    Когда: { $datetime }
    Адрес: { $address }
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

partner-event-label-participation = <b>Стоимость:</b> { $value } ₽

partner-event-label-age = <b>Возраст:</b> { $value }

partner-event-text-template =

    <b>{ $name }</b>
    ────────────

    { $datetime }
    { $address }
    { $participation }
    { $age_block }

    { $description_block }

general-registration-age-group = { $range } лет
