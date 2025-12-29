start-hello =
    Hello, { $username }!

    Welcome to the Bachelors Club ✨

    If you’re here, it means you’re open to знакомства and общения

    This bot will help you:

    • sign up for club events
    • track your registrations
    • connect with people who share your goals

    📢 Our main channel — @hol_club

    Ready to start? Choose an action 👇
start-events-title = Your events
start-events-list-button = my registrations
start-events-empty = You are not signed up for any events yet.
start-events-item = { $name } — { $datetime }{ $tags }
start-events-page = Page { $current } of { $total }
start-events-prev-button = ◀️
start-events-next-button = ▶️
start-event-paid-tag = [paid]
start-event-past-tag = [already passed]
partner-events-title = Your events
partner-events-list-button = Мy events
partner-events-empty = You have no created events yet.
partner-events-item = { $name } — { $datetime } ({ $paid }/{ $total })
partner-events-page = Page { $current } of { $total }
partner-events-prev-button = ◀️
partner-events-next-button = ▶️
start-event-details-text = { $name }
    { $datetime }{ $tags }
start-event-details-missing = Could not find the event.

              Welcome to the Singles Club ✨

              If you are here, it means you are open to meeting people and socializing

              This bot will help you:

                • sign up for club events
                • keep track of your registrations
                • get closer to people with similar goals

              📢 <b>Our main channel</b> — @hol_club

              Ready to start? Then choose an action 👇

will-delete = This message will be deleted after { $delay ->
                [one] { $delay } second
               *[other] { $delay } seconds
              }

stranger = Stranger

help-command = The following commands are available as a mini-demonstration of the capabilities:

               <b>Delayed deletion of messages:</b>

               /del - Send a message that will be deleted automatically in a few seconds

               <b>Background and scheduled tasks:</b>
               
               /simple - Create a simple task that will start running immediately
               /delay - Create a task that will start running in 5 seconds
               /periodic - Create a dynamically scheduled periodic task that will run every 2 minutes
               /del_periodic - Delete all periodic tasks

               <b>Common commands:</b>

               /lang - Select the interface language 
               /start - Restart the bot
               /help - View this help

               <b>Partnership:</b>

               /partner_request - Submit a partnership request

simple-task = Simple task

task-soon = The task will be completed soon!

periodic-task = This is a dynamically scheduled periodic task

no-periodic-tasks = Периодические задачи отсутствуют в расписании

periodic-tasks-deleted = Периодические задачи успешно удалены!

about-author = About author

about-author-link = https://t.me/toBeAnMLspecialist/935

free-course = 🤖 Free course on bots

free-course-link = https://stepik.org/course/120924

advanced-course = 🚀 Advanced course on bots

advanced-course-link = https://stepik.org/a/153850

mlpodcast = Machine Learning Podcast

mlpodcast-link = https://mlpodcast.mave.digital/

back-button = ◀️ Back

save-button = ✅ Save

set-lang-menu = <b>Please select the language of the bot interface</b>

                The 🇬🇧 <b>English</b> language is selected

ru-lang = 🇷🇺 Russian

en-lang = 🇬🇧 English

fr-lang = 🇫🇷 Franch

de-lang = 🇩🇪 German

lang-saved = ✅ The language settings have been saved successfully!

partner-request-forbidden = You already have partner or admin permissions.

partner-request-sent = Your partnership request has been sent. An admin will review it.

partner-request-pending = Your request is already under review.

partner-request-approved = Your request is already approved. Partner role is active.

partner-approve-forbidden = You do not have permission to approve requests.


partner-approve-missing = Partnership request not found.

partner-approve-already = This request is already approved.

partner-approve-user-missing = User not found.

partner-approve-success = Request approved. User { $user_id } is now a partner.

partner-request-button = Partnership request

partner-request-channel-text = Want to become a partner? Tap the button below.

partner-request-channel-posted = The request button was posted to the channel.

partner-request-channel-failed = Could not send the message to the channel.

partner-request-admin-notify = Partnership request from { $username } (id: { $user_id }).
partner-request-list-header = Partnership requests: { $count }.
partner-request-list-empty = No partnership requests found.
partner-request-list-item = User { $user_id } wants to become a partner.
partner-request-list-button = View requests
partner-request-contact-button = Contact

partner-request-approve-button = Approve

partner-request-reject-button = Reject

partner-request-rejected = Your partnership request was rejected.

partner-request-already-rejected = This request is already rejected.

partner-request-invalid = Invalid request data.

partner-decision-approved = Request approved.

partner-decision-rejected = Request rejected.

partner-request-channel-missing = Partner channel is not set. Add EVENTS_CHANNEL to .env.

partner-event-create-button = Create event

partner-event-create-button = Create event

partner-event-forbidden = You don't have permission to create events.

partner-event-name-prompt = Enter the event title (from <b>{ $min }</b> to <b>{ $max }</b> characters).

partner-event-name-invalid = The title must be from <b>{ $min }</b> to <b>{ $max }</b> characters.

partner-event-image-prompt = Send an event image or skip this step.

partner-event-skip-button = Skip

partner-event-datetime-prompt = Enter date and time (e.g. <b>2026.01.01 00:00</b>).

partner-event-datetime-invalid = Invalid date/time format. Example: <b>2026.01.01 00:00</b>.

partner-event-datetime-past = The date must be in the future. Example: <b>2026.01.01 00:00</b>.

partner-event-address-prompt = Enter the address in <b>Moscow</b> with exact details up to the house number.


partner-event-address-empty = No addresses found. Try refining the query.

partner-event-address-select-prompt = Choose an address from the suggestions.

partner-event-address-invalid = Invalid address selection. Please try again.

partner-event-address-house-missing = Please include the house number in the address.
partner-event-address-city-moscow = The address must be in <b>Moscow</b>.

partner-event-description-prompt = Enter the description (from { $min } to { $max } characters).

partner-event-description-invalid = The description must be from { $min } to { $max } characters.

partner-event-participation-prompt = Choose the participation type.

partner-event-participation-free = Free

partner-event-participation-paid = Paid

partner-event-price-prompt = Enter the price (up to <b>{ $max }</b> RUB).

partner-event-price-invalid = Invalid price. Maximum <b>{ $max }</b> RUB.

partner-event-age-prompt = Enter the age group (e.g., <b>18+</b> or <b>35-45</b>) or skip.

partner-event-age-invalid = Invalid age group. Use the <b>18+</b> or <b>35-45</b> format.

partner-event-notify-prompt = Notify bot users?

partner-event-notify-yes = Yes

partner-event-notify-no = No

partner-event-preview-title = Event preview:

partner-event-preview-photo-attached = A photo will be attached.

partner-event-preview-trimmed = The text was shortened to fit the caption limit.

partner-event-publish-button = Publish

partner-event-edit-name-button = Edit title

partner-event-edit-image-button = Edit image

partner-event-edit-datetime-button = Edit date/time

partner-event-edit-address-button = Edit address

partner-event-edit-description-button = Edit description

partner-event-edit-participation-button = Edit participation

partner-event-edit-price-button = Edit price

partner-event-edit-age-button = Edit age group

partner-event-edit-notify-button = Edit notifications

partner-event-going-button = I'm in
partner-event-going-forbidden = Only users with the user status can register.
partner-event-going-missing = Could not find the event for registration.
partner-event-going-already = You are already registered for this event.
partner-event-going-done = You are registered.
partner-event-going-thanks =
    Thanks for registering for the event “{ $event_name }”!

    If you have any questions, please contact the organizer: { $partner_username }.

    If you have already paid, please <b>don’t forget to tap the “I have paid” button</b> at the bottom of the registration form.
partner-event-going-notify-partner = User { $username } (id: { $user_id }) registered for “{ $event_name }”.
partner-event-going-contact-user-button = Contact the user
partner-event-going-contact-partner-button = Ask about the event
partner-event-going-paid-button = I have paid
partner-event-paid-missing = Could not find the event for payment.
partner-event-paid-not-registered = You are not registered for this event.
partner-event-paid-already = Payment is already marked.
partner-event-paid-done = Thanks! We notified the organizer.
partner-event-paid-notify-partner =
    User { $username } (id: { $user_id }) reported payment for the event “{ $event_name }”.

    Please confirm the payment and send the receipt by replying to this message.
partner-event-paid-receipt-forbidden = Could not accept a receipt for this event.
partner-event-paid-receipt-saved = Receipt saved.
partner-event-paid-receipt-failed = Could not save the receipt. Please try again.

partner-event-view-post-button = View post
partner-event-registrations-title = Registrations: { $count }
partner-event-registrations-button = Registrations: { $paid }/{ $total }
partner-event-registrations-empty = No registrations yet.
partner-event-registrations-item = { $user_label } { $paid_tag }
partner-event-registrations-paid-tag = [paid]

partner-event-publish-success = Event published.

partner-event-publish-failed = Failed to publish the event.

partner-event-publish-already = The event is already published.

partner-event-publish-in-progress = Publishing is already in progress.

partner-event-channel-missing = Event channel is not set. Add EVENTS_CHANNEL to .env.

partner-event-notify-users = New event: { $name }. Details in { $channel }.

partner-event-notify-sent = Notifications sent: { $count }.

partner-event-label-datetime = 📅 Date and time: { $value }

partner-event-label-address = 📍 Address: { $value }

partner-event-label-participation = 👥 Participation: { $value } $

partner-event-label-price = 💳 Price: { $value }

partner-event-label-age = 🎯 Age group: { $value }

partner-event-text-template =
    <b>{ $name }</b>
    ────────────

    { $datetime }
    { $address }
    { $participation }
    { $age_block }

    { $description_block }
