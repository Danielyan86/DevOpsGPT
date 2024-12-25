# Jenkins Configuration Guide

## Introduction

The Jenkins main service runs in a local Docker container, with the agent running in the local environment.

## Jenkins Server Setup

1. Start Jenkins with Docker:

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v /Users/sheldon/AI_project_OPS/jenkins_home:/var/jenkins_home \
  -v /Users/sheldon/AI_project_OPS/jenkins_workspace:/var/jenkins_home/workspace \
  jenkins/jenkins:lts
```

2. Create a Jenkins job:

   - Create a new pipeline job
   - Configure the job settings
   - Save the configuration

3. Create a Jenkins token:
   - Navigate to User Settings
   - Select API Token section
   - Generate new token
   - Save the token for ChatOps service

## Configuration Steps

### Jenkins Agent Setup

Based on the command from Jenkins page to start the agent:
![Jenkins Agent Setup](./pictures/jenkins_agent.png)

### Slack Integration

Configure Slack token in Jenkins:
![Slack Configuration](./pictures/slack_configuration.png)

### Jenkins Token Configuration

Set up authentication token:
![Jenkins Token](./pictures/jenkins_token.png)
