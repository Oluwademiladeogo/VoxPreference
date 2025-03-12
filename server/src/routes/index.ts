import { Router } from "express";
import { health } from "../controllers/health";
const router: Router = Router();

router.get("/", health);
export const mainRouter: Router = router;
