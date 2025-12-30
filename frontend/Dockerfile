FROM node:20

WORKDIR /app

# Copy dependency files first
COPY package.json package-lock.json* ./

RUN npm install --legacy-peer-deps

# Copy source
COPY . .

EXPOSE 3000

CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "3000"]
