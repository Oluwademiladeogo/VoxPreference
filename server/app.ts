import express, { Application } from "express";
import cors from "cors";
import { mainRouter } from "./src/routes";
import helmet from "helmet";
const app: Application = express();
app.use(express.json());
app.use(cors());
app.use(helmet())
app.use("/api", mainRouter);

export default app;
