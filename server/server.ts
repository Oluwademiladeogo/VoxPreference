import express from "express";
import cors from "cors";
import { config } from "dotenv";
config();
const app = express();
app.use(express.json());
app.use(cors());

app.get("/health", (req, res) => {
  res.send("OK");
});
const port = process.env.PORT || 3000;
app.listen(port, () => {
  process.env.NODE_ENV == "development"
    ? console.log(`server running on port ${port}`)
    : "";
});
