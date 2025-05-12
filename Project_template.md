## Изучите [README.md](.\README.md) файл и структуру проекта.

# Задание 1

Спроектируйте TO-BE архитектуру КиноБездны. Для этого разделите всю систему на отдельные домены и организуйте интеграционное взаимодействие и единую точку вызова сервисов. Результат представьте в виде контейнерной диаграммы в нотации С4, после чего добавьте ссылку на файл в этот [шаблон](ссылка).

# Задание 2

### 1. Proxy
Команда КиноБездны уже выделила сервис метаданных о фильмах movies. Теперь вам нужно реализовать бесшовный переход. Для этого примените паттерна Strangler Fig в части реализации прокси-сервиса (API Gateway), с помощью которого можно будет постепенно переключать траффик, используя фиче-флаг.


Реализуйте сервис на любом языке программирования в ./src/microservices/proxy.
Конфигурация для запуска сервиса через docker-compose уже добавлена.
```yaml
  proxy-service:
    build:
      context: ./src/microservices/proxy
      dockerfile: Dockerfile
    container_name: cinemaabyss-proxy-service
    depends_on:
      - monolith
      - movies-service
      - events-service
    ports:
      - "8000:8000"
    environment:
      PORT: 8000
      MONOLITH_URL: http://monolith:8080
      #монолит
      MOVIES_SERVICE_URL: http://movies-service:8081 #сервис movies
      EVENTS_SERVICE_URL: http://events-service:8082 
      GRADUAL_MIGRATION: "true" # вкл/выкл простого фиче-флага
      MOVIES_MIGRATION_PERCENT: "50" # процент миграции
    networks:
      - cinemaabyss-network
```

- После реализации запустите Postman тесты. Все они (кроме events) должны быть зеленые.
- Отправьте запросы к API Gateway:
   ```bash
   curl http://localhost:8000/api/movies
   ```
- Протестируйте постепенный переход, изменив переменную окружения MOVIES_MIGRATION_PERCENT в файле docker-compose.yml.


### 2. Kafka
 Вам нужно проверить гипотезу, насколько просто будет реализовать применение Kafka в данной архитектуре. Для этого сделайте MVP сервиса events, который при вызове API будет создавать и сам же читать сообщения в топике Kafka.

    - Разработайте сервис на любом языке программирования с consumer'ами и producer'ами.
    - Реализуйте простой API, при вызове которого будут создаваться события User/Payment/Movie и обрабатываться внутри сервиса с записью в лог
    - Добавьте в docker-compose новый сервис, kafka там уже есть

Тесты для проверки этого API вызываются при запуске npm run test:local из папки tests/postman. 
Приложите скриншот тестов и скриншот состояния топиков Kafka из UI http://localhost:8090 

# Задание 3

Чтобы лучше масштабироваться и повысить надежность, команда КиноБездны уже начала переезд в Kubernetes. Вам как архитектору осталось реализовать:
 - CI/CD для сборки прокси сервиса;
 - необходимые конфигурационные файлы для переключения трафика.


### CI/CD

 В папке .github/worflows доработайте деплой новых сервисов proxy и events в docker-build-push.yml так, чтобы при отправке коммита в ваш репозиторий API-тесты работали корректно.

Доработайте: 
```yaml
on:
  push:
    branches: [ main ]
    paths:
      - 'src/**'
      - '.github/workflows/docker-build-push.yml'
  release:
    types: [published]
```
и добавьте необходимые шаги в блок:
```yaml
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to the Container registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

```
После того как сборка отработает и в github registry появятся ваши образы, переходите к блоку настройки Kubernetes. Если у вас "зеленая" сборка и "зеленые" тесты, то значит, все сделано правильно.


### Proxy в Kubernetes

#### Шаг 1
Для деплоя в kubernetes залогиньтесь в docker registry на Github.
1. Создайте Personal Access Token (PAT) https://github.com/settings/tokens и class с правом read:packages.
   
2. В src/kubernetes/*.yaml (event-service, monolith, movies-service и proxy-service) отредактируйте путь до ваших образов: 
```bash
 spec:
      containers:
      - name: events-service
        image: ghcr.io/ваш логин/имя репозитория/events-service:latest
```
3. Добавьте в секрет src/kubernetes/dockerconfigsecret.yaml в поле:
```bash
 .dockerconfigjson: значение в base64 файла ~/.docker/config.json
```

4. Если в ~/.docker/config.json нет значения для аутентификации: 
```json
{
        "auths": {
                "ghcr.io": {
                       тут пусто
                }
        }
}
```
то выполните и добавьте: 

```json 
 "auth": "имя пользователя:токен в base64"
```

Чтобы получить значение в base64, выполните команду: 
```bash
 echo -n ваш_логин:ваш_токен | base64
```

Заполните config.json и прогоните содержимое через base64:

```bash
cat .docker/config.json | base64
```

Полученное значение добавьте в: 

```bash
 .dockerconfigjson: значение в base64 файла ~/.docker/config.json
```

#### Шаг 2

  Доработайте src/kubernetes/event-service.yaml и src/kubernetes/proxy-service.yaml

  - Создайте Deployment и Service.
  - Доработайте ingress.yaml, чтобы с помощью тестов можно было проверить создание событий.
  - Выполните дальшейшие шаги для поднятия кластера:

  1. Создайте namespace:
  ```bash
  kubectl apply -f src/kubernetes/namespace.yaml
  ```
  
  2. Создайте секреты и переменные:
  ```bash
  kubectl apply -f src/kubernetes/configmap.yaml
  kubectl apply -f src/kubernetes/secret.yaml
  kubectl apply -f src/kubernetes/dockerconfigsecret.yaml
  kubectl apply -f src/kubernetes/postgres-init-configmap.yaml
  ```

  3. Разверните базу данных:
  ```bash
  kubectl apply -f src/kubernetes/postgres.yaml
  ```

  4. Теперь вызовите команду:
  ```bash
  kubectl -n cinemaabyss get pod
  ```
  После этого вы должны увидить следующее:

  NAME         READY   STATUS    
  postgres-0   1/1     Running   

  5. Разверните Kafka:
  ```bash
  kubectl apply -f src/kubernetes/kafka/kafka.yaml
  ```

  Проверьте, что у вас запущено 3 пода. Если что-то не так, то посмотрите логи:
  ```bash
  kubectl -n cinemaabyss logs имя_пода (например - kafka-0)
  ```

  6. Разверните монолит:
  ```bash
  kubectl apply -f src/kubernetes/monolith.yaml
  ```
  
  7. Разверните микросервисы:
  ```bash
  kubectl apply -f src/kubernetes/movies-service.yaml
  kubectl apply -f src/kubernetes/events-service.yaml
  ```
  
  8. Разверните прокси-сервис:
  ```bash
  kubectl apply -f src/kubernetes/proxy-service.yaml
  ```

  После запуска и поднятия подов нужно вывести команду:
  ```bash
  kubectl -n cinemaabyss get pod
  ```

  В результате у вас должно получиться: 

  NAME                              READY   STATUS    

  events-service-7587c6dfd5-6whzx   1/1     Running  

  kafka-0                           1/1     Running   

  monolith-8476598495-wmtmw         1/1     Running  

  movies-service-6d5697c584-4qfqs   1/1     Running  

  postgres-0                        1/1     Running  

  proxy-service-577d6c549b-6qfcv    1/1     Running  

  zookeeper-0                       1/1     Running 

  
  9. Теперь добавьте ingress:

  ```bash
  minikube addons enable ingress
  ```
  ```bash
  kubectl apply -f src/kubernetes/ingress.yaml
  ```
  
  10. Добавьте в /etc/hosts
  127.0.0.1 cinemaabyss.example.com

  
  11. Следующим шагом вызовите:
      
  ```bash
  minikube tunnel
  ```
  
  12. Вызовите https://cinemaabyss.example.com/api/movies. В результате у вас должен вывестись список фильмов. 
      
  Кстати, поэкспериментируйте со значением MOVIES_MIGRATION_PERCENT в src/kubernetes/configmap.yaml. Так вы сможете убедится, что вызов movies полностью уходят в новый сервис.

  12. Запустите тесты из папки tests/postman
      
  ```bash
   npm run test:kubernetes
  ```
  Часть тестов с health-чек упадет, но создание событий отработает. Откройте логи event-service и сделайте скриншот обработки событий.


#### Шаг 3
Добавьте 2 скриншота: 
1) вывода при вызове https://cinemaabyss.example.com/api/movies;
2) вывода event-service после тестов.


# Задание 4
Чтобы в будущем упростить обновление и развертывание архитектуры, вам нужно создать Helm-чарты для прокси-сервиса и проверить их работу.

1. Перейдите в директорию helm и отредактируйте файл values.yaml: 

```yaml
# Proxy service configuration
proxyService:
  enabled: true
  image:
    repository: ghcr.io/db-exp/cinemaabysstest/proxy-service
    tag: latest
    pullPolicy: Always
  replicas: 1
  resources:
    limits:
      cpu: 300m
      memory: 256Mi
    requests:
      cpu: 100m
      memory: 128Mi
  service:
    port: 80
    targetPort: 8000
    type: ClusterIP
```

- Вместо ghcr.io/db-exp/cinemaabysstest/proxy-service напишите свой путь до образа для всех сервисов.
  
- Для imagePullSecret проставьте свое значение. Его нужно скопировать из конфигурации kubernetes:
  
  ```yaml
  imagePullSecrets:
      dockerconfigjson: ewoJImF1dGhzIjogewoJCSJnaGNyLmlvIjogewoJCQkiYXV0aCI6ICJaR0l0Wlhod09tZG9jRjl2UTJocVZIa3dhMWhKVDIxWmFVZHJOV2hRUW10aFVXbFZSbTVaTjJRMFNYUjRZMWM9IgoJCX0KCX0sCgkiY3JlZHNTdG9yZSI6ICJkZXNrdG9wIiwKCSJjdXJyZW50Q29udGV4dCI6ICJkZXNrdG9wLWxpbnV4IiwKCSJwbHVnaW5zIjogewoJCSIteC1jbGktaGludHMiOiB7CgkJCSJlbmFibGVkIjogInRydWUiCgkJfQoJfSwKCSJmZWF0dXJlcyI6IHsKCQkiaG9va3MiOiAidHJ1ZSIKCX0KfQ==
  ```

2. В папке ./templates/services заполните шаблоны для proxy-service.yaml и events-service.yaml. Тут важно опираться именно на свою kubernetes-конфигурацию, потому что Helm создает шаблоны для быстрого обновления и установки.
   
```yaml
template:
    metadata:
      labels:
        app: proxy-service
    spec:
      containers:
       Тут ваша конфигурация
```

3. Теперь проверьте установку.
   Для этого сначала удалите установку в ручном режиме: 

```bash
kubectl delete all --all -n cinemaabyss
kubectl delete  namespace cinemaabyss
```
После чего запустите: 
```bash
helm install cinemaabyss .\src\kubernetes\helm --namespace cinemaabyss --create-namespace
```
Если в процессе вы столкнетесь с такого рода ошибкой:

```code
[2025-04-08 21:43:38,780] ERROR Fatal error during KafkaServer startup. Prepare to shutdown (kafka.server.KafkaServer)
kafka.common.InconsistentClusterIdException: The Cluster ID OkOjGPrdRimp8nkFohYkCw doesn't match stored clusterId Some(sbkcoiSiQV2h_mQpwy05zQ) in meta.properties. The broker is trying to join the wrong cluster. Configured zookeeper.connect may be wrong.
```

то проверьте развертывание:

```bash
kubectl get pods -n cinemaabyss
minikube tunnel
```

После чего вызовите:
https://cinemaabyss.example.com/api/movies


# Задание 5 
Компания КиноБездна планирует активно развиваться. Перед вами стоит задача – повысить надежность и безопасность реализации сетевых паттернов типа Circuit Breaker и канареечного деплоя. Для этого вам нужно развернуть istio и настроить circuit breaker для monolith и movies сервисов.

.\helm.exe repo add istio https://istio-release.storage.googleapis.com/charts .\helm.exe repo update

.\helm install istio-base istio/base -n istio-system --set defaultRevision=default --create-namespace .\helm install istio-ingressgateway istio/gateway -n istio-system .\helm install istiod istio/istiod -n istio-system --wait

helm install cinemaabyss .\src\kubernetes\helm --namespace cinemaabyss --create-namespace

--kubectl label namespace cinemaabyss istio.io/inject=enabled

kubectl label namespace cinemaabyss istio-injection=enabled --overwrite

kubectl get namespace -L istio-injection

kubectl apply -f .\src\kubernetes\circuit-breaker-config.yaml -n cinemaabyss

Тестирование

### fortio
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.25/samples/httpbin/sample-client/fortio-deploy.yaml -n cinemaabyss

Получаем имя под
FORTIO_POD=$(kubectl get pod -n cinemaabyss | grep fortio | awk '{print $1}')

kubectl exec -n cinemaabyss $FORTIO_POD -c fortio -- fortio load -c 50 -qps 0 -n 500 -loglevel Warning http://movies-service:8081/api/movies

Например,

kubectl exec -n cinemaabyss fortio-deploy-b6757cbbb-7c9qg -c fortio -- fortio load -c 50 -qps 0 -n 500 -loglevel Warning http://movies-service:8081/api/movies

Вывод будет типа такого

IP addresses distribution: 10.106.113.46:8081: 421 Code 200 : 79 (15.8 %) Code 500 : 22 (4.4 %) Code 503 : 399 (79.8 %)

Можно еще проверить статистику

kubectl exec -n cinemaabyss fortio-deploy-b6757cbbb-7c9qg -c istio-proxy -- pilot-agent request GET stats | grep movies-service | grep pending

И там смотрим

cluster.outbound|8081||movies-service.cinemaabyss.svc.cluster.local;.upstream_rq_pending_total: 311 - столько раз срабатывал circuit breaker You can see 21 for the upstream_rq_pending_overflow value which means 21 calls so far have been flagged for circuit breaking.

Делаем скриншот тестирования и прикладываем к работе

## Удаляем все

Установите https://istio.io/latest/docs/reference/commands/istioctl/

```bash
istioctl uninstall --purge 
kubectl delete namespace istio-system 
kubectl delete all --all -n cinemaabyss 
kubectl delete namespace cinemaabyss
```
