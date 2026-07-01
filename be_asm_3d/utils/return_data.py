from rest_framework import status
from rest_framework.response import Response


class ReturnDeletedDataMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        deleted_data = serializer.data

        self.perform_destroy(instance)

        return Response({
            'item': deleted_data
        }, status=status.HTTP_200_OK)