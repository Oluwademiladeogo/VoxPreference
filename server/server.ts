import app from "./app"
import { config } from "dotenv";
config();
const port = process.env.PORT || 3000;
app.listen(port, () => {
  process.env.NODE_ENV == "development"
    ? console.log(`server running on port ${port}`)
    : "";
});
