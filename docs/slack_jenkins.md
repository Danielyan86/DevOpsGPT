# slack

1. Install slack app
2. Create a workspace and and a channel

# jenkins

1. Install jenkins with docker

   ```bash
   docker run -d --name jenkins \
   -p 8080:8080 -p 50000:50000 \
   -v /Users/sheldon/AI_project_OPS/jenkins_home:/var/jenkins_home \
   -v /Users/sheldon/AI_project_OPS/jenkins_workspace:/var/jenkins_home/workspace \
   jenkins/jenkins:lts

   ```

2. Create a job
3. Create a token

# Ngrok

1. Install ngrok
2. Create a tunnel
