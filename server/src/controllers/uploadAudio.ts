import { Request, Response } from "express";

export const uploadAudio = (req: Request, res: Response) => {
    const fileName = req.body?.fileName;
    const fileDescription = req.body?.fileDescription;
    console.log(req.file, fileName, fileDescription);
    res.status(200).json({ message: "File successfully uploaded" });
  };
  