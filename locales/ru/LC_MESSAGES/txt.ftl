start-hello = Привет, { $username }!

              Добро пожаловать в Клуб холостяков ✨

              Если ты здесь — значит, открыт(а) к знакомствам, общению

              Этот бот поможет тебе:

                • записываться на мероприятия клуба
                • следить за своими регистрациями
                • быть ближе к людям с похожими целями

              📢 <b>Наш основной канал</b> — @hol_club

              Готов(а) начать? Тогда выбирай действие 👇

will-delete = Это сообщение удалится через { $delay ->
                [one] { $delay } секунду
                [few] { $delay } секунды
               *[other] { $delay } секунд
              }

stranger = Странник

help-command = В качестве мини-демонстрации возможностей доступны следующие команды:

               <b>Отложенное удаление сообщений:</b>

               /del - Отправить сообщение, которое будет удалено автоматически через несколько секунд

               <b>Фоновые и планируемые по времени задачи:</b>
               
               /simple - Создать простую задачу, которая начнёт выполняться сразу
               /delay - Создать задачу, которая начнёт выполняться через 5 секунд
               /periodic - Создать динамически планируемую периодическую задачу, которая будет выполняться раз в 2 минуты
               /del_periodic - Удалить все периодические задачи

               <b>Общие команды:</b>

               /lang - Выбрать язык интерфейса
               /start - Перезапустить бота
               /help - Посмотреть эту справку

               <b>Партнерство:</b>

               /partner_request - Отправить заявку на партнерство

simple-task = Простая задача

task-soon = Задача выполнится скоро!

periodic-task = Это динамически планируемая периодическая задача

no-periodic-tasks = Периодические задачи отсутствуют в расписании

periodic-tasks-deleted = Периодические задачи успешно удалены!

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

partner-event-price-prompt = Введите стоимость (до <b>{ $max }</b> ₽).

partner-event-price-invalid = Некорректная стоимость. Максимум <b>{ $max }</b> ₽.

partner-event-age-prompt = Введите возрастную группу (например, <b>18+</b> или <b>35-45</b>) или пропустите.

partner-event-age-invalid = Некорректная возрастная группа. Используйте формат <b>18+</b> или <b>35-45</b>.

partner-event-notify-prompt = Отправлять уведомление пользователям бота?

partner-event-notify-yes = Да

partner-event-notify-no = Нет

partner-event-preview-title = Превью события:

partner-event-preview-photo-attached = Фото будет прикреплено.

partner-event-preview-trimmed = Текст был сокращен из-за лимита подписи.

partner-event-publish-button = Опубликовать

partner-event-edit-name-button = Редактировать название

partner-event-edit-image-button = Редактировать изображение

partner-event-edit-datetime-button = Редактировать дату и время

partner-event-edit-address-button = Редактировать адрес

partner-event-edit-description-button = Редактировать описание

partner-event-edit-participation-button = Редактировать тип участия

partner-event-edit-price-button = Редактировать стоимость

partner-event-edit-age-button = Редактировать возраст

partner-event-edit-notify-button = Редактировать уведомления

partner-event-going-button = Я пойду

partner-event-view-post-button = Смотреть пост

partner-event-publish-success = Событие опубликовано.

partner-event-publish-failed = Не удалось опубликовать событие.

partner-event-publish-already = Событие уже опубликовано.

partner-event-publish-in-progress = Публикация уже выполняется.

partner-event-channel-missing = Не указан канал для событий. Добавьте EVENTS_CHANNEL в .env.

partner-event-notify-users = Новое событие: { $name }. Подробности в { $channel }.

partner-event-notify-sent = Уведомления отправлены: { $count }.

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
