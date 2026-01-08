# Use Node.js 20 Alpine as base image
FROM node:20-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package.json ./

# Install dependencies
RUN npm install

# Copy all source files
COPY . .

# Build the Next.js application
RUN npm run build

# Expose the port Next.js runs on
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start the Next.js server
CMD ["npm", "start"]
