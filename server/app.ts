import express, { Application } from "express";
import cors from "cors";
import { config } from "dotenv";
import { mainRouter } from "./src/routes";
config();
const app: Application = express();
app.use(express.json());
app.use(cors());
app.use("/api", mainRouter);

export default app;
