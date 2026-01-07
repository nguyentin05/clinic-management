import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.notifications.services import NotificationService

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"notifications_{self.user.id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        unread_count = await self.get_unread_count()

        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": unread_count
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'mark_as_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_as_read(notification_id)

                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    "type": "unread_count",
                    "count": unread_count
                }))

            elif message_type == 'get_unread_count':
                count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    "type": "unread_count",
                    "count": count
                }))

        except Exception as e:
            print(str(e))

    async def notification_message(self, event):
        notification = event.get("notification")

        #seri bước cuối trước khi gửi đi
        await self.send(text_data=json.dumps({
            "type": "new_notification",
            "notification": notification
        }))

    async def unread_count_update(self, event):
        count = event.get("count")

        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": count
        }))


    #chuyển db sang async ở luồng khác để ko lag
    @database_sync_to_async
    def get_unread_count(self):
        return NotificationService.get_unread_count(self.user)

    @database_sync_to_async
    def mark_notification_as_read(self, id):
        return NotificationService.mark_as_read(id, self.user)