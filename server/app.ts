import express, { Application } from "express";
import cors from "cors";
import helmet from "helmet";
import healthRouter from "./src/routes/health"
import uploadAudioRouter from "./src/routes/uploadAudio"
const app: Application = express();
app.use(express.json());
app.use(cors());
app.use(helmet())
app.use("/api/health", healthRouter);
app.use("/api/upload-audio", uploadAudioRouter)

export default app;
