FROM node:20

WORKDIR /app

# Copy dependency files first
COPY package.json package-lock.json* ./

# Install dependencies with explicit optional dependencies
RUN npm cache clean --force && \
    npm install --legacy-peer-deps && \
    npm install --no-save @rollup/rollup-linux-x64-gnu

# Copy source
COPY . .

EXPOSE 3000

CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "3000"]
