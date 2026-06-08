import { Router } from "express";
import extractPanelsRouter from "./extract-panels";

const router = Router();

router.use(extractPanelsRouter);

export default router;
