import { Router } from "express";
import { health } from "../controllers/health";
const router: Router = Router();

router.get("/health", health);
export default router;
