FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev port
EXPOSE 3000

# Start Vite dev server with host flag for container networking
CMD ["npm", "run", "dev", "--", "--host"]
