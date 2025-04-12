import multer from "multer";
import { Request, Response, Router } from "express";
const router = Router();
//store in tmp to process data but on consent, transfer to diff folder to train model
const upload = multer({ dest: "tmp/uploads/" });

const uploadFiles = (req: Request, res: Response) => {
  const fileName = req.body.fileName;
  const fileDescription = req.body.fileDescription;
  console.log(req.file, fileName, fileDescription);
  res.status(200).json({ message: "File successfully uploaded" });
};

router.post("/", upload.single("audioFile"), uploadFiles);
export default router;
