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
               /partner_approve &lt;user_id&gt; - Одобрить заявку (только для админов)
               /partner_post - Опубликовать кнопку заявки в канале (только для админов)

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

partner-approve-usage = Использование: /partner_approve &lt;user_id&gt;

partner-approve-missing = Заявка на партнерство не найдена.

partner-approve-already = Эта заявка уже одобрена.

partner-approve-user-missing = Пользователь не найден.

partner-approve-success = Заявка одобрена. Пользователь { $user_id } теперь партнер.

partner-request-button = Заявка на партнерство

partner-request-channel-text = Хочешь стать партнером? Нажми кнопку ниже.

partner-request-channel-posted = Сообщение с заявкой опубликовано в канале.

partner-request-channel-failed = Не удалось отправить сообщение в канал.

partner-request-admin-notify = Заявка на партнерство от { $username } (id: { $user_id }).

partner-request-approve-button = Принять

partner-request-reject-button = Отклонить

partner-request-rejected = Ваша заявка на партнерство отклонена.

partner-request-already-rejected = Эта заявка уже отклонена.

partner-request-invalid = Некорректные данные заявки.

partner-decision-approved = Заявка одобрена.

partner-decision-rejected = Заявка отклонена.

partner-request-channel-missing = Не указан канал для заявок. Добавьте PARTNER_CHANNEL в .env.
