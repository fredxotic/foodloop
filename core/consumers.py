import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # SECURITY FIX: Use the logged-in user, not the URL parameter
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            # Reject connection if user is not logged in
            await self.close()
            return

        # Create a group specific to this user ID
        self.room_group_name = f'notifications_{self.user.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Notifications are usually push-only (Server -> Client).
        # We generally don't need to handle incoming JSON for simple notifications.
        pass

    async def notification_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))