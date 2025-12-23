start-hello = Hello, { $username }!

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
               /partner_approve &lt;user_id&gt; - Approve a request (admins only)
               /partner_post - Post the request button in the channel (admins only)

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

partner-approve-usage = Usage: /partner_approve &lt;user_id&gt;

partner-approve-missing = Partnership request not found.

partner-approve-already = This request is already approved.

partner-approve-user-missing = User not found.

partner-approve-success = Request approved. User { $user_id } is now a partner.

partner-request-button = Partnership request

partner-request-channel-text = Want to become a partner? Tap the button below.

partner-request-channel-posted = The request button was posted to the channel.

partner-request-channel-failed = Could not send the message to the channel.

partner-request-admin-notify = Partnership request from { $username } (id: { $user_id }).

partner-request-approve-button = Approve

partner-request-reject-button = Reject

partner-request-rejected = Your partnership request was rejected.

partner-request-already-rejected = This request is already rejected.

partner-request-invalid = Invalid request data.

partner-decision-approved = Request approved.

partner-decision-rejected = Request rejected.

partner-request-channel-missing = Partner channel is not set. Add PARTNER_CHANNEL to .env.
