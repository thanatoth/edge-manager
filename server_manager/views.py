from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import EdgeServer, Client, Cluster, Area
from django.db.models import Q, Max
from .serializer import EdgeServerSerializer, ClientSerializer, ClusterSerializer, AreaSerializer

from strategy import allocator

from rest_framework.decorators import action

#strategy_main = "RA"
#strategy_main = "NS"
#strategy_main = "LCA"
strategy_main = "RLCA"
#strategy_main = "RLCCA" #Relaiton and Locality concious Cooperative Client Assingment

# Create your views here.

class EdgeServerViewSet(viewsets.ModelViewSet):
    queryset = EdgeServer.objects.all()
    serializer_class = EdgeServerSerializer

    #エッジサーバーから呼び出されるAPI
    @action(detail=False, methods=["post"])
    def post(self, request):
        application_id = request.GET['application_id'] #シミュレーター上では指定

        if EdgeServer.objects.all().count() == 0:
            server_id = 1
        else:
            server_id = EdgeServer.objects.all().aggregate(Max('server_id'))['server_id__max'] + 1 #server_idは各アプリケーションで指定

        #データの生成
        x = request.POST['x']
        y = request.POST['y']
        capacity = request.POST['capacity']
        server = EdgeServer.objects.create(application_id = application_id, server_id = server_id, x = x, y = y, capacity = capacity, used = 0)
        server.save()

        allocator.clustering(application_id)

        serializer = self.get_serializer(server)

        return Response(serializer.data, status=status.HTTP_200_OK)

    #定期的な位置更新
    @action(detail=False, methods=["put"])
    def update_used(self, request):
        application_id = request.GET["application_id"]
        server_id = request.GET["server_id"]
        server = self.queryset.get(Q(application_id = application_id), Q(server_id = server_id))
        used = request.POST["used"]
        capacity = request.POST["capacity"]

        server.used = used
        server.capacity = capacity
        server.save()

        allocator.clustering(application_id)
        serializer = self.get_serializer(server)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #データベース管理用API
    @action(detail=False, methods=["get"])
    def get(self, request):
        application_id = request.GET["application_id"]
        server_id = request.GET["server_id"]
        server = self.queryset.get(Q(application_id = application_id), Q(server_id = server_id))
        serializer = self.get_serializer(server)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_all(self, request):
        application_id = request.GET["application_id"]
        servers = EdgeServer.objects.filter(application_id=application_id)
        serializer = self.get_serializer(servers, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"])
    def delete_all(self, request):
        application_id = request.GET["application_id"]
        EdgeServer.objects.filter(application_id=application_id).delete()

        servers = EdgeServer.objects.filter(application_id=application_id)
        serializer = self.get_serializer(servers, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)



#クライアントサイドのアプリケーションから呼び出されるAPI
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    #クライアントの登録
    @action(detail=False, methods=["post"])
    def post(self, request):
        application_id = request.GET['application_id'] #シミュレーター上では指定

        if  Client.objects.all().count() == 0:
            client_id = 1
        else:
             client_id = Client.objects.all().aggregate(Max('client_id'))['client_id__max'] + 1
        print('client_id', client_id)
        x = request.POST['x']
        y = request.POST['y']

        client = Client.objects.create(application_id = application_id, client_id = client_id, x = x, y = y)

        #home serverの割り当て
        new_home_server_id = allocator.allocate(application_id, client_id, strategy="RA", weight=0)
        client.home = EdgeServer.objects.get(server_id = new_home_server_id)
        client.save()

        serializer = self.get_serializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #定期的な位置更新
    @action(detail=False, methods=["put"])
    def update_location(self, request):
        application_id = request.GET["application_id"]
        client_id = request.GET["client_id"]
        client = Client.objects.get(Q(application_id = application_id), Q(client_id = client_id))
        x = request.POST['x']
        y = request.POST['y']

        client.x = x
        client.y = y
        client.save()

        serializer = self.get_serializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #定期的なhome serverの更新
    @action(detail=False, methods=["put"])
    def update_home(self, request):

        application_id = request.GET["application_id"]
        client_id = request.GET["client_id"]
        weight = int(request.POST['weight'])
        client = Client.objects.get(Q(application_id = application_id), Q(client_id = client_id))

        '''
        1. 該当クライアントのデータを取得
        2. 現在位置をもとに, home serverを更新
        '''

        #application_idの指定により, 領域の大きさ（Kの大きさ）をテーブルより取得
        #一旦ランダムに配置
        new_home_server_id = allocator.allocate(application_id, client_id, strategy_main, weight)
        client.home = EdgeServer.objects.get(server_id = new_home_server_id)
        client.save()

        serializer = self.get_serializer(client)
        allocator.clustering(application_id)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #データベース管理用API
    @action(detail=False, methods=["get"])
    def get(self, request, pk = None):
        application_id = request.GET["application_id"]
        client_id = request.GET["client_id"]
        client = self.queryset.get(Q(application_id = application_id), Q(client_id = client_id))
        serializer = self.get_serializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_all(self, request):
        application_id = request.GET["application_id"]
        clients = Client.objects.filter(application_id=application_id)
        serializer = self.get_serializer(clients, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"])
    def delete_all(self, request):
        application_id = request.GET["application_id"]
        Client.objects.filter(application_id=application_id).delete()

        clients = Client.objects.filter(application_id=application_id)
        serializer = self.get_serializer(clients, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #シミュレーション用API
    @action(detail=False, methods=["post"])
    def post_from_simulator(self, request):
        application_id = request.GET['application_id'] #シミュレーター上では指定
        client_id = request.POST['client_id']

        x = request.POST['x']
        y = request.POST['y']

        if len(Client.objects.filter(Q(application_id = application_id), Q(client_id = client_id))) == 0:
            client = Client.objects.create(application_id = application_id, client_id = client_id, x = x, y = y)
        else:
            return Response(status=status.HTTP_200_OK)

        #home serverの割り当て
        new_home_server_id = allocator.allocate(application_id, client_id, strategy="RA", weight=0)
        client.home = EdgeServer.objects.get(server_id = new_home_server_id)
        client.save()

        serializer = self.get_serializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ClusterViewSet(viewsets.ModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer
    def get_all(self, request):
        application_id = request.GET["application_id"]
        clusters = Cluster.objects.filter(application_id=application_id)
        serializer = self.get_serializer(clusters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"])
    def delete_all(self, request):
        application_id = request.GET["application_id"]
        Cluster.objects.filter(application_id=application_id).delete()

        clusters = Cluster.objects.filter(application_id=application_id)
        serializer = self.get_serializer(clusters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer

    @action(detail=False, methods=["put"])
    def update_number_of_coopserver(self,request):
        number_of_coopserver=request.POST['number_of_coopserver']
        area = Area.objects.get(size = 2)
        area.avg_n_cooperative_server=number_of_coopserver
        area.save()
        serializer = self.get_serializer(area)
        return Response(serializer.data, status=status.HTTP_200_OK)
