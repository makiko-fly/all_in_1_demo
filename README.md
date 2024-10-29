# Microservices Demo

## Overview

This is a demo project illustrating the design of microservices, containerization using docker, and deployment in k8s.

k8s dashboard: https://k8s-dashboard.chenfei-demo.com/

crypto page: https://crypto-web.chenfei-demo.com/static/crypto_24h_stats.html


## Feature List
- Backend:
  - service discovery, list microservice status [finished]
  - dao layer, access and modify user data in mysql [finished]
  - auth service, login, register and list users [finished]
  - service_kline, websocket client for binance futures api [finished]
  - service_kline, clickhouse manager [finished]
  - service_kline, redis stream manager [finished]
- FrontEnd:
  - login page [finished]
  - dashboard page, display services and user list [finished]
  - crypto futures 24H stats page [finished]
  - crypto futures tick level trades page [finished]
  - big task, use react or vue...
- DevOps:
  - set up a k8s cluster on aws eks [finished]
  - deploy frontend code [finished]
  - install k8s dashboard and expose it on the internet [finished]
  - apply and set up customized doamin chenfei-demo.com [finished]
  - configure https for endpoints [finished]
  - continuous integration...


