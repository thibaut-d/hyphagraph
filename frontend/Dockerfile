FROM node:20

WORKDIR /app

# Copy dependency files first
COPY package.json package-lock.json* ./

RUN npm install

# Copy source
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
