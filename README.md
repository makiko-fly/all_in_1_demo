# Microservices Demo

## Overview

This is a demo project illustrating the design of microservices, containerization using docker, and deployment in k8s.

I wrote a simple front-end that can access some of the APIs provided by api-gateway, display the data so that viewers can have a better understanding of the project.


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
  - FrontEnd: dashboard page, display services and user list [finished]
  - FrontEnd: crypto futures 24H stats page [finished]
  - FrontEnd: crypto futures tick level trades page [finished]
  - FrontEnd: big task, use react or vue...
- DevOps:
  - set up a k8s cluster on aws eks [finished]
  - deploy frontend code [finished]
  - install k8s dashboard and expose it on the internet [finished]
  - apply and set up customized doamin chenfei-demo.com [finished]
  - configure https for endpoints [finished]
  - continuous integration...


