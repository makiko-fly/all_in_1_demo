# Microservices Demo

## Overview

This is a demo project illustrating the design of microservices, containerization using docker, and deployment in k8s.

I wrote a simple front-end that can access some of the APIs provided by api-gateway, display the data so that viewers can have a better understanding of the project.


## Planned Feature List
- Backend: service discovery, list microservice status [finished]
- Backend: dao layer, access and modify user data in mysql [finished]
- Backend: auth service, login, register and list users [finished]
- Backend: to be defined
- FrontEnd: login page [finished]
- FrontEnd: dashboard page, display services and user list [finished]
- FrontEnd: crypto futures monitor page [finished]
- FrontEnd: big task, use react or vue
- DevOps: set up a k8s cluster on aws eks [finished]
- DevOps: deploy front-end and backend onto aws eks
  - deploy frontend [finished]
  - deploy backend
    - install ebs csi driver and deploy mysql as a service [finished]
    - deploy clickhouse
    - deploy redis
    - deploy backend code
- DevOps: continuous integration

