import multer from "multer";
import { Request, Response, Router } from "express";
import { uploadAudio } from "../controllers/uploadAudio";
const router = Router();
//store in tmp to process data but on consent, transfer to diff folder to train model
const upload = multer({ dest: "tmp/uploads/" });

router.post("/", upload.single("audioFile"), uploadAudio);
export default router;
